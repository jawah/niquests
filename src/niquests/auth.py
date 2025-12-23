"""
requests.auth
~~~~~~~~~~~~~

This module contains the authentication handlers for Requests.
"""

from __future__ import annotations

import contextvars
import hashlib
import os
import re
import time
import typing
from base64 import b64encode
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .cookies import extract_cookies_to_jar
from .utils import parse_dict_header

if typing.TYPE_CHECKING:
    from .models import PreparedRequest

CONTENT_TYPE_FORM_URLENCODED: str = "application/x-www-form-urlencoded"
CONTENT_TYPE_MULTI_PART: str = "multipart/form-data"


def _basic_auth_str(username: str | bytes, password: str | bytes) -> str:
    """Returns a Basic Auth string."""

    if isinstance(username, str):
        username = username.encode("utf-8")

    if isinstance(password, str):
        password = password.encode("utf-8")

    authstr = "Basic " + b64encode(b":".join((username, password))).strip().decode()

    return authstr


class AsyncAuthBase:
    """Base class that all asynchronous auth implementations derive from"""

    async def __call__(self, r: PreparedRequest) -> PreparedRequest:
        raise NotImplementedError("Auth hooks must be callable.")


class AuthBase:
    """Base class that all synchronous auth implementations derive from"""

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        raise NotImplementedError("Auth hooks must be callable.")


class BearerTokenAuth(AuthBase):
    """Simple token injection in Authorization header"""

    def __init__(self, token: str):
        self.token = token

    def __eq__(self, other) -> bool:
        return self.token == getattr(other, "token", None)

    def __ne__(self, other) -> bool:
        return not self == other

    def __call__(self, r):
        detect_token_type: list[str] = self.token.split(" ", maxsplit=1)

        if len(detect_token_type) == 1:
            r.headers["Authorization"] = f"Bearer {self.token}"
        else:
            r.headers["Authorization"] = self.token

        return r


class HTTPBasicAuth(AuthBase):
    """Attaches HTTP Basic Authentication to the given Request object."""

    def __init__(self, username: str | bytes, password: str | bytes):
        self.username = username
        self.password = password

    def __eq__(self, other) -> bool:
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other) -> bool:
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = _basic_auth_str(self.username, self.password)
        return r


class HTTPProxyAuth(HTTPBasicAuth):
    """Attaches HTTP Proxy Authentication to a given Request object."""

    def __call__(self, r):
        r.headers["Proxy-Authorization"] = _basic_auth_str(self.username, self.password)
        return r


@dataclass
class DigestAuthState:
    """Container for digest auth state per task/thread"""

    init: bool = False
    last_nonce: str = ""
    nonce_count: int = 0
    chal: typing.Mapping[str, str | None] = field(default_factory=dict)
    pos: int | None = None
    num_401_calls: int | None = None


class HTTPDigestAuth(AuthBase):
    """Attaches HTTP Digest Authentication to the given Request object."""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        # Keep state in per-thread local storage
        self._thread_local: contextvars.ContextVar[DigestAuthState] = contextvars.ContextVar("digest_auth_state")

    def init_per_thread_state(self) -> None:
        # Ensure state is initialized just once per-thread
        state = self._thread_local.get(None)

        if state is None or not state.init:
            self._thread_local.set(DigestAuthState(init=True))

    def build_digest_header(self, method: str, url: str) -> str | None:
        state = self._thread_local.get(None)

        assert state is not None

        realm = state.chal["realm"]
        nonce = state.chal["nonce"]
        qop = state.chal.get("qop")
        algorithm = state.chal.get("algorithm")
        opaque = state.chal.get("opaque")

        hash_utf8: typing.Callable[[str | bytes], str] | None = None

        if algorithm is None:
            _algorithm = "MD5"
        else:
            _algorithm = algorithm.upper()
        # lambdas assume digest modules are imported at the top level
        if _algorithm == "MD5" or _algorithm == "MD5-SESS":

            def md5_utf8(x: str | bytes) -> str:
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.md5(x).hexdigest()

            hash_utf8 = md5_utf8
        elif _algorithm == "SHA":

            def sha_utf8(x: str | bytes) -> str:
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha1(x).hexdigest()

            hash_utf8 = sha_utf8
        elif _algorithm == "SHA-256":

            def sha256_utf8(x: str | bytes) -> str:
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha256(x).hexdigest()

            hash_utf8 = sha256_utf8
        elif _algorithm == "SHA-512":

            def sha512_utf8(x: str | bytes) -> str:
                if isinstance(x, str):
                    x = x.encode("utf-8")
                return hashlib.sha512(x).hexdigest()

            hash_utf8 = sha512_utf8
        else:
            raise ValueError(f"'{_algorithm}' hashing algorithm is not supported")

        KD = lambda s, d: hash_utf8(f"{s}:{d}")  # noqa:E731

        if hash_utf8 is None:
            return None

        # XXX not implemented yet
        entdig = None
        p_parsed = urlparse(url)
        #: path is request-uri defined in RFC 2616 which should not be empty
        path = p_parsed.path or "/"
        if p_parsed.query:
            path += f"?{p_parsed.query}"

        A1 = f"{self.username}:{realm}:{self.password}"
        A2 = f"{method}:{path}"

        HA1 = hash_utf8(A1)
        HA2 = hash_utf8(A2)

        if nonce == state.last_nonce:
            state.nonce_count += 1
        else:
            state.nonce_count = 1
        ncvalue = f"{state.nonce_count:08x}"
        s = str(state.nonce_count).encode("utf-8")

        assert nonce is not None

        s += nonce.encode("utf-8")
        s += time.ctime().encode("utf-8")
        s += os.urandom(8)

        cnonce = hashlib.sha1(s).hexdigest()[:16]
        if _algorithm == "MD5-SESS":
            HA1 = hash_utf8(f"{HA1}:{nonce}:{cnonce}")

        if not qop:
            respdig = KD(HA1, f"{nonce}:{HA2}")
        elif qop == "auth" or "auth" in qop.split(","):
            noncebit = f"{nonce}:{ncvalue}:{cnonce}:auth:{HA2}"
            respdig = KD(HA1, noncebit)
        else:
            # XXX handle auth-int.
            return None

        state.last_nonce = nonce

        # XXX should the partial digests be encoded too?
        base = f'username="{self.username}", realm="{realm}", nonce="{nonce}", uri="{path}", response="{respdig}"'
        if opaque:
            base += f', opaque="{opaque}"'
        if algorithm:
            base += f', algorithm="{algorithm}"'
        if entdig:
            base += f', digest="{entdig}"'
        if qop:
            base += f', qop="auth", nc={ncvalue}, cnonce="{cnonce}"'

        return f"Digest {base}"

    def handle_redirect(self, r, **kwargs) -> None:
        """Reset num_401_calls counter on redirects."""
        state = self._thread_local.get(None)

        assert state is not None

        if r.is_redirect:
            state.num_401_calls = 1

    async def async_handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed (async version).

        :rtype: requests.Response
        """
        state = self._thread_local.get(None)

        assert state is not None

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            state.num_401_calls = 1
            return r

        if state.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(state.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "digest" in s_auth.lower() and state.num_401_calls < 2:  # type: ignore[operator]
            state.num_401_calls += 1  # type: ignore[operator]
            pat = re.compile(r"digest ", flags=re.IGNORECASE)
            state.chal = parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            await r.content
            await r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers["Authorization"] = self.build_digest_header(prep.method, prep.url)
            _r = await r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        state.num_401_calls = 1
        return r

    def handle_401(self, r, **kwargs):
        """
        Takes the given response and tries digest-auth, if needed.

        :rtype: requests.Response
        """
        state = self._thread_local.get(None)

        assert state is not None

        # If response is not 4xx, do not auth
        # See https://github.com/psf/requests/issues/3772
        if not 400 <= r.status_code < 500:
            state.num_401_calls = 1
            return r

        if state.pos is not None:
            # Rewind the file position indicator of the body to where
            # it was to resend the request.
            r.request.body.seek(state.pos)
        s_auth = r.headers.get("www-authenticate", "")

        if "digest" in s_auth.lower() and state.num_401_calls < 2:  # type: ignore[operator]
            state.num_401_calls += 1  # type: ignore[operator]
            pat = re.compile(r"digest ", flags=re.IGNORECASE)
            state.chal = parse_dict_header(pat.sub("", s_auth, count=1))

            # Consume content and release the original connection
            # to allow our new request to reuse the same one.
            r.content
            r.close()
            prep = r.request.copy()
            extract_cookies_to_jar(prep._cookies, r.request, r.raw)
            prep.prepare_cookies(prep._cookies)

            prep.headers["Authorization"] = self.build_digest_header(prep.method, prep.url)
            _r = r.connection.send(prep, **kwargs)
            _r.history.append(r)
            _r.request = prep

            return _r

        state.num_401_calls = 1
        return r

    def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        state = self._thread_local.get(None)
        assert state is not None
        # If we have a saved nonce, skip the 401
        if state.last_nonce:
            r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
        try:
            state.pos = r.body.tell()
        except AttributeError:
            # In the case of HTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            state.pos = None
        # Register sync hooks only - use AsyncHTTPDigestAuth for async sessions
        r.register_hook("response", self.handle_401)
        r.register_hook("response", self.handle_redirect)
        state.num_401_calls = 1

        return r

    def __eq__(self, other) -> bool:
        return all(
            [
                self.username == getattr(other, "username", None),
                self.password == getattr(other, "password", None),
            ]
        )

    def __ne__(self, other) -> bool:
        return not self == other


class AsyncHTTPDigestAuth(HTTPDigestAuth, AsyncAuthBase):
    """Async version of HTTPDigestAuth for use with AsyncSession.

    Attaches HTTP Digest Authentication to the given Request object and handles
    401 responses asynchronously.

    Example usage::

        >>> import niquests
        >>> auth = niquests.auth.AsyncHTTPDigestAuth('user', 'pass')
        >>> async with niquests.AsyncSession() as session:
        ...     r = await session.get('https://httpbin.org/digest-auth/auth/user/pass', auth=auth)
        ...     print(r.status_code)
        200
    """

    async def __call__(self, r):
        # Initialize per-thread state, if needed
        self.init_per_thread_state()
        state = self._thread_local.get(None)
        assert state is not None
        # If we have a saved nonce, skip the 401
        if state.last_nonce:
            r.headers["Authorization"] = self.build_digest_header(r.method, r.url)
        try:
            state.pos = r.body.tell()
        except AttributeError:
            # In the case of AsyncHTTPDigestAuth being reused and the body of
            # the previous request was a file-like object, pos has the
            # file position of the previous body. Ensure it's set to
            # None.
            state.pos = None
        # Register async hooks only
        r.register_hook("response", self.async_handle_401)
        r.register_hook("response", self.handle_redirect)
        state.num_401_calls = 1

        return r

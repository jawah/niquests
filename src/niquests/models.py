"""
requests.models
~~~~~~~~~~~~~~~

This module contains the primary objects that power Requests.
"""

from __future__ import annotations

import asyncio
import codecs
import datetime

# Import encoding now, to avoid implicit import later.
# Implicit import within threads may cause LookupError when standard library is in a ZIP,
# such as in Embedded Python. See https://github.com/psf/requests/issues/3578.
import encodings.idna  # noqa: F401
import warnings

try:
    import orjson as _json  # type: ignore[import]
except ImportError:
    import json as _json

import typing

if typing.TYPE_CHECKING:
    from typing_extensions import Literal

from collections.abc import Mapping
from http import cookiejar as cookielib
from http.cookiejar import CookieJar
from io import UnsupportedOperation
from urllib.parse import urlencode, urlsplit, urlunparse

from charset_normalizer import from_bytes

from ._typing import (
    AsyncBodyType,
    AsyncHttpAuthenticationType,
    BodyFormType,
    BodyType,
    CookiesType,
    HeadersType,
    HookCallableType,
    HookType,
    HttpAuthenticationType,
    HttpMethodType,
    MultiPartFilesAltType,
    MultiPartFilesType,
    QueryParameterType,
)
from ._vendor.kiss_headers import Headers, parse_it
from .auth import BearerTokenAuth, HTTPBasicAuth
from .cookies import (
    RequestsCookieJar,
    _copy_cookie_jar,
    cookiejar_from_dict,
    get_cookie_header,
)
from .exceptions import (
    ChunkedEncodingError,
    ConnectionError,
    ContentDecodingError,
    HTTPError,
    InvalidJSONError,
    InvalidURL,
    MultiplexingError,
    StreamConsumedError,
)
from .exceptions import JSONDecodeError as RequestsJSONDecodeError
from .exceptions import SSLError as RequestsSSLError
from .hooks import default_hooks
from .packages.urllib3 import (
    AsyncHTTPResponse as BaseAsyncHTTPResponse,
)
from .packages.urllib3 import (
    BaseHTTPResponse,
    ConnectionInfo,
    ResponsePromise,
)
from .packages.urllib3.contrib.webextensions import (
    RawExtensionFromHTTP,
    ServerSideEventExtensionFromHTTP,
    WebSocketExtensionFromHTTP,
)
from .packages.urllib3.contrib.webextensions._async import (
    AsyncRawExtensionFromHTTP,
    AsyncServerSideEventExtensionFromHTTP,
    AsyncWebSocketExtensionFromHTTP,
)
from .packages.urllib3.exceptions import (
    DecodeError,
    LocationParseError,
    ProtocolError,
    ReadTimeoutError,
    SSLError,
)
from .packages.urllib3.fields import RequestField
from .packages.urllib3.filepost import choose_boundary, encode_multipart_formdata
from .packages.urllib3.util import parse_url
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (
    astream_decode_response_unicode,
    get_auth_from_url,
    guess_filename,
    iter_slices,
    parse_header_links,
    parse_scheme,
    requote_uri,
    stream_decode_response_unicode,
    super_len,
    to_key_val_list,
)

#: The set of HTTP status codes that indicate an automatically
#: processable redirect.
REDIRECT_STATI = (
    #  301
    codes.moved,  # type: ignore[attr-defined]
    # 302
    codes.found,  # type: ignore[attr-defined]
    # 303
    codes.other,  # type: ignore[attr-defined]
    # 307
    codes.temporary_redirect,  # type: ignore[attr-defined]
    # 308
    codes.permanent_redirect,  # type: ignore[attr-defined]
)

DEFAULT_REDIRECT_LIMIT = 30
CONTENT_CHUNK_SIZE = 10 * 1024
ITER_CHUNK_SIZE = -1


class TransferProgress:
    def __init__(self):
        self.total: int = 0
        self.content_length: int | None = None
        self.is_completed: bool = False
        self.any_error: bool = False

    @property
    def percentage(self) -> float | None:
        if self.content_length is None:
            return None

        return round((self.total / self.content_length) * 100.0, 3)

    def __repr__(self) -> str:
        if self.content_length:
            return f"<Progress {self.percentage} % ({self.total} / {self.content_length})>"
        return f"<Progress {self.total} bytes sent ({'in progress' if self.is_completed is False else 'completed'})>"


class Request:
    """A user-created :class:`Request <Request>` object.

    Used to prepare a :class:`PreparedRequest <PreparedRequest>`, which is sent to the server.

    :param method: HTTP method to use.
    :param url: URL to send.
    :param headers: dictionary of headers to send.
    :param files: dictionary of {filename: fileobject} files to multipart upload.
    :param data: the body to attach to the request. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param json: json for the body to attach to the request (if files or data is not specified).
    :param params: URL parameters to append to the URL. If a dictionary or
        list of tuples ``[(key, value)]`` is provided, form-encoding will
        take place.
    :param auth: Auth handler or (user, pass) tuple.
    :param cookies: dictionary or CookieJar of cookies to attach to this request.
    :param hooks: dictionary of callback hooks, for internal usage.

    Usage::

      >>> import niquests
      >>> req = niquests.Request('GET', 'https://httpbin.org/get')
      >>> req.prepare()
      <PreparedRequest [GET]>
    """

    def __init__(
        self,
        method: HttpMethodType | None = None,
        url: str | None = None,
        headers: HeadersType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        data: BodyType | AsyncBodyType | None = None,
        params: QueryParameterType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        cookies: CookiesType | None = None,
        hooks: HookType | None = None,
        json: typing.Any | None = None,
        base_url: str | None = None,
    ):
        # Default empty dicts for dict params.
        data = [] if data is None else data
        files = [] if files is None else files
        headers = CaseInsensitiveDict() if headers is None else headers
        params = {} if params is None else params
        hooks = {} if hooks is None else hooks

        self.hooks: HookType[Response | PreparedRequest] = default_hooks()
        for k, v in list(hooks.items()):
            self.register_hook(event=k, hook=v)

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.json = json
        self.params = params
        self.auth = auth
        self.cookies = cookies
        self.base_url = base_url

    @property
    def oheaders(self) -> Headers:
        return parse_it(self.headers)

    def __repr__(self) -> str:
        return f"<Request [{self.method}]>"

    def register_hook(
        self,
        event: str,
        hook: HookCallableType[Response | PreparedRequest] | list[HookCallableType[Response | PreparedRequest]],
    ) -> None:
        """Properly register a hook."""

        if event not in self.hooks:
            raise ValueError(f'Unsupported event specified, with event name "{event}"')

        if callable(hook):
            self.hooks[event].append(hook)
        elif isinstance(hook, list):
            self.hooks[event].extend(h for h in hook if callable(h))

    def deregister_hook(self, event: str, hook: HookCallableType[Response | PreparedRequest]) -> bool:
        """Deregister a previously registered hook.
        Returns True if the hook existed, False if not.
        """

        try:
            self.hooks[event].remove(hook)
            return True
        except ValueError:
            return False

    def prepare(self) -> PreparedRequest:
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for transmission and returns it."""
        p = PreparedRequest()

        p.prepare(
            method=self.method,
            url=self.url,
            headers=self.headers,
            files=self.files,
            data=self.data,
            json=self.json,
            params=self.params,
            auth=self.auth,
            cookies=self.cookies,
            hooks=self.hooks,
            base_url=self.base_url,
        )

        return p


class PreparedRequest:
    """The fully mutable :class:`PreparedRequest <PreparedRequest>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import niquests
      >>> req = niquests.Request('GET', 'https://httpbin.org/get')
      >>> r = req.prepare()
      >>> r
      <PreparedRequest [GET]>

      >>> s = niquests.Session()
      >>> s.send(r)
      <Response HTTP/2 [200]>
    """

    _pending_async_auth: AsyncHttpAuthenticationType

    def __init__(self) -> None:
        #: HTTP verb to send to the server.
        self.method: HttpMethodType | None = None
        #: HTTP URL to send the request to.
        self.url: str | None = None
        #: dictionary of HTTP headers.
        self.headers: CaseInsensitiveDict | None = None
        # The `CookieJar` used to create the Cookie header will be stored here
        # after prepare_cookies is called
        self._cookies: RequestsCookieJar | CookieJar | None = None
        #: request body to send to the server.
        self.body: BodyType | AsyncBodyType | None = None
        #: dictionary of callback hooks, for internal usage.
        self.hooks: HookType[Response | PreparedRequest] = default_hooks()
        #: integer denoting starting position of a readable file-like body.
        self._body_position: int | object | None = None
        #: valuable intel about the opened connection.
        self.conn_info: ConnectionInfo | None = None
        #: marker about if OCSP post-handshake verification took place.
        self.ocsp_verified: bool | None = None
        #: upload progress if any.
        self.upload_progress: TransferProgress | None = None
        #: internal usage only. warn us that we should re-compute content-length and await auth() outside of PreparedRequest.
        self._asynchronous_auth: bool = False

    @property
    def oheaders(self) -> Headers:
        return parse_it(self.headers)

    def prepare(
        self,
        method: HttpMethodType | None = None,
        url: str | None = None,
        headers: HeadersType | None = None,
        files: MultiPartFilesType | MultiPartFilesAltType | None = None,
        data: BodyType | AsyncBodyType | None = None,
        params: QueryParameterType | None = None,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None = None,
        cookies: CookiesType | None = None,
        hooks: HookType[Response | PreparedRequest] | None = None,
        json: typing.Any | None = None,
        base_url: str | None = None,
    ) -> None:
        """Prepares the entire request with the given parameters."""

        self.prepare_method(method)
        self.prepare_url(url, params, base_url=base_url)
        self.prepare_headers(headers)
        self.prepare_cookies(cookies)
        self.prepare_body(data, files, json)
        self.prepare_auth(auth)

        # Note that prepare_auth must be last to enable authentication schemes
        # such as OAuth to work on a fully prepared request.

        # This MUST go after prepare_auth. Authenticators could add a hook
        self.prepare_hooks(hooks)

    def __repr__(self) -> str:
        return f"<PreparedRequest [{self.method}]>"

    def copy(self) -> PreparedRequest:
        p = PreparedRequest()
        p.method = self.method
        p.url = self.url
        p.headers = self.headers.copy() if self.headers is not None else None
        p._cookies = _copy_cookie_jar(self._cookies)
        p.body = self.body
        p.hooks = self.hooks
        p._body_position = self._body_position
        return p

    def prepare_method(self, method: HttpMethodType | None) -> None:
        """Prepares the given HTTP method."""
        self.method = method.upper() if method else method

    def prepare_url(
        self,
        url: str | None,
        params: QueryParameterType | None,
        *,
        base_url: str | None = None,
    ) -> None:
        """Prepares the given HTTP URL."""
        assert url is not None, "Missing URL in PreparedRequest"

        if base_url is not None:
            if parse_scheme(url, default="") == "":
                if base_url.endswith("/"):
                    base_url = base_url[:-1]
                if not url.startswith("/"):
                    url = f"/{url}"
                url = base_url + url

        #: Accept objects that have string representations.
        #: We're unable to blindly call unicode/str functions
        #: as this will include the bytestring indicator (b'')
        #: on python 3.x.
        #: https://github.com/psf/requests/pull/2238
        if isinstance(url, bytes):
            url = url.decode("utf8")
        else:
            url = str(url)

        # Remove leading whitespaces from url
        url = url.lstrip()

        # Don't do any URL preparation for non-HTTP schemes like `mailto`,
        # `data` etc to work around exceptions from `url_parse`, which
        # handles RFC 3986 only.
        if not parse_scheme(url).startswith("http"):
            self.url = url
            return

        # Support for unicode domain names and paths.
        try:
            scheme, auth, host, port, path, query, fragment = parse_url(url)
        except LocationParseError as e:
            raise InvalidURL(*e.args)

        if not host:
            raise InvalidURL(f"Invalid URL {url!r}: No host supplied")

        if host.startswith(("*", ".")):
            raise InvalidURL("URL has an invalid label.")

        if (not path or "%" not in path) and not auth and not params and not host.startswith("xn--"):
            self.url = url
            return

        # Carefully reconstruct the network location
        netloc = auth or ""
        if netloc:
            netloc += "@"
        netloc += host
        if port:
            netloc += f":{port}"

        # Bare domains aren't valid URLs.
        if not path:
            path = "/"

        if params:
            if isinstance(params, bytes):
                params = params.decode("utf-8")

            enc_params = self._encode_params(params)
            if enc_params:
                if isinstance(enc_params, (bytes, bytearray)):
                    enc_params = enc_params.decode("utf-8")
                if query:
                    query = f"{query}&{enc_params}"
                else:
                    query = enc_params

        self.url = requote_uri(urlunparse([scheme, netloc, path, None, query, fragment]))

    def prepare_headers(self, headers: HeadersType | None) -> None:
        """Prepares the given HTTP headers."""

        self.headers = CaseInsensitiveDict()

        if headers:
            if isinstance(headers, list):
                self.headers.update(CaseInsensitiveDict(headers))
            else:
                for header in headers.items():
                    name, value = header
                    if isinstance(name, bytes):
                        name = name.decode()
                    self.headers[name] = value

    def prepare_body(
        self,
        data: BodyType | AsyncBodyType | None,
        files: MultiPartFilesType | MultiPartFilesAltType | None,
        json: typing.Any | None = None,
    ) -> None:
        """Prepares the given HTTP body data."""

        # Check if file, fo, generator, iterator.
        # If not, run through normal process.

        assert self.headers is not None

        # Nottin' on you.
        body: BodyType | AsyncBodyType | None = None
        content_type: str | None = None
        enforce_form_data = False

        if not data and json is not None:
            # urllib3 requires a bytes-like body. Python 2's json.dumps
            # provides this natively, but Python 3 gives a Unicode string.
            content_type = "application/json;charset=utf-8"
            json_kwargs = {}

            if not hasattr(_json, "orjson"):
                json_kwargs["allow_nan"] = False

            try:
                body = _json.dumps(json, **json_kwargs)
            except ValueError as ve:
                raise InvalidJSONError(ve, request=self)

            if isinstance(body, str):
                body = body.encode("utf-8")

        is_stream = hasattr(data, "__aiter__") or all(
            [
                hasattr(data, "__iter__"),
                not isinstance(data, (str, list, tuple, Mapping)),
            ]
        )

        if is_stream:
            try:
                length = super_len(data)
            except (TypeError, AttributeError, UnsupportedOperation):
                length = None

            body = data

            if body is not None and hasattr(body, "tell"):
                # Record the current file position before reading.
                # This will allow us to rewind a file in the event
                # of a redirect.
                try:
                    self._body_position = body.tell()
                except OSError:
                    # This differentiates from None, allowing us to catch
                    # a failed `tell()` later when trying to rewind the body
                    self._body_position = object()

            if files:
                raise NotImplementedError("Streamed bodies and files are mutually exclusive.")

            if length:
                self.headers["Content-Length"] = str(length)
            elif body:
                self.headers["Transfer-Encoding"] = "chunked"
        else:
            # Multi-part file uploads.
            if files:
                if not (
                    isinstance(
                        data,
                        (
                            list,
                            dict,
                        ),
                    )
                    or data is None
                ):
                    raise ValueError(f"Conflicting parameters. Cannot pass files with given data: type({type(data)})")
                # mypy seems to lose its way here.
                (body, content_type) = self._encode_files(files, data)  # type: ignore[arg-type]
            else:
                if data:
                    enforce_form_data = "content-type" in self.headers and "multipart/form-data" in self.headers["content-type"]

                    if enforce_form_data:
                        form_data_boundary = (
                            self.oheaders.content_type.get("boundary")  # type: ignore[union-attr]
                            if enforce_form_data
                            and self.oheaders.content_type.has_many("boundary") is False  # type: ignore[union-attr]
                            and self.oheaders.content_type.get("boundary") is not None  # type: ignore[union-attr]
                            else choose_boundary()
                        )
                    else:
                        form_data_boundary = None

                    body = self._encode_params(
                        data,  # type: ignore[arg-type]
                        boundary_for_multipart=form_data_boundary,  # type: ignore[arg-type]
                    )
                    if isinstance(data, str) or hasattr(data, "read"):
                        content_type = None
                    else:
                        if not enforce_form_data:
                            content_type = "application/x-www-form-urlencoded"
                        else:
                            content_type = f"multipart/form-data; boundary={form_data_boundary}"

            assert isinstance(body, (list, dict)) is False
            self.prepare_content_length(body)

            # Add content-type if it wasn't explicitly provided.
            if content_type and ("content-type" not in self.headers):
                self.headers["Content-Type"] = content_type
            elif content_type and enforce_form_data:
                self.headers["Content-Type"] = content_type

        self.body = body

    def prepare_content_length(self, body: BodyType | AsyncBodyType | None) -> None:
        """Prepare Content-Length header based on request method and body"""
        assert self.headers is not None

        if body is not None:
            length = super_len(body)
            if length:
                # If length exists, set it. Otherwise, we fallback
                # to Transfer-Encoding: chunked.
                self.headers["Content-Length"] = str(length)
        elif self.method not in ("GET", "HEAD") and self.headers.get("Content-Length") is None:
            # Set Content-Length to 0 for methods that can have a body
            # but don't provide one. (i.e. not GET or HEAD)
            self.headers["Content-Length"] = "0"

    def prepare_auth(
        self,
        auth: HttpAuthenticationType | AsyncHttpAuthenticationType | None,
        url: str = "",
    ) -> None:
        """Prepares the given HTTP auth data."""

        assert self.url is not None, "Cannot invoke prepare_auth method with incomplete PreparedRequest"

        # If no Auth is explicitly provided, extract it from the URL first.
        if auth is None:
            url_auth = get_auth_from_url(self.url)
            auth = url_auth if any(url_auth) else None

        if auth:
            if isinstance(auth, tuple) and len(auth) == 2:
                # special-case basic HTTP auth
                auth = HTTPBasicAuth(*auth)
            elif isinstance(auth, str):
                auth = BearerTokenAuth(auth)

            if not callable(auth):
                raise ValueError("Unexpected non-callable authentication. Did you pass unsupported tuple to auth argument?")

            self._asynchronous_auth = (
                hasattr(auth, "__call__") and asyncio.iscoroutinefunction(auth.__call__)
            ) or asyncio.iscoroutinefunction(auth)

            if not self._asynchronous_auth:
                # Allow auth to make its changes.
                r = auth(self)

                # Update self to reflect the auth changes.
                self.__dict__.update(r.__dict__)

                # Recompute Content-Length
                self.prepare_content_length(self.body)
            else:
                self._pending_async_auth = auth  # type: ignore[assignment]

    def prepare_cookies(self, cookies: CookiesType | None) -> None:
        """Prepares the given HTTP cookie data.

        This function eventually generates a ``Cookie`` header from the
        given cookies using cookielib. Due to cookielib's design, the header
        will not be regenerated if it already exists, meaning this function
        can only be called once for the life of the
        :class:`PreparedRequest <PreparedRequest>` object. Any subsequent calls
        to ``prepare_cookies`` will have no actual effect, unless the "Cookie"
        header is removed beforehand.
        """
        assert self.headers is not None, "method prepare_cookies must be invoked after prepare_headers"

        if isinstance(cookies, cookielib.CookieJar):
            self._cookies = cookies
        else:
            self._cookies = cookiejar_from_dict(cookies)

        cookie_header = get_cookie_header(self._cookies, self)
        if cookie_header is not None:
            self.headers["Cookie"] = cookie_header

    def prepare_hooks(self, hooks) -> None:
        """Prepares the given hooks."""
        # hooks can be passed as None to the prepare method and to this
        # method. To prevent iterating over None, simply use an empty list
        # if hooks is False-y
        hooks = hooks or []
        for event in hooks:
            self.register_hook(event, hooks[event])

    def register_hook(self, event, hook) -> None:
        """Properly register a hook."""

        if event not in self.hooks:
            raise ValueError(f'Unsupported event specified, with event name "{event}"')

        if callable(hook):
            self.hooks[event].append(hook)
        elif hasattr(hook, "__iter__"):
            self.hooks[event].extend(h for h in hook if callable(h))

    def deregister_hook(self, event: str, hook) -> bool:
        """Deregister a previously registered hook.
        Returns True if the hook existed, False if not.
        """

        try:
            self.hooks[event].remove(hook)
            return True
        except ValueError:
            return False

    @property
    def path_url(self) -> str:
        """Build the path URL to use."""
        assert self.url is not None
        url = []

        p = urlsplit(self.url)

        path = p.path
        if not path:
            path = "/"

        url.append(path)

        query = p.query
        if query:
            url.append("?")
            url.append(query)

        return "".join(url)

    @staticmethod
    def _encode_params(
        data: QueryParameterType | BodyFormType | typing.IO,
        boundary_for_multipart: str | None = None,
    ) -> str | bytes | bytearray:
        """Encode parameters in a piece of data.

        Will successfully encode parameters when passed as a dict or a list of
        2-tuples. Order is retained if data is a list of 2-tuples but arbitrary
        if parameters are supplied as a dict.
        """

        if isinstance(data, (str, bytes, bytearray)):
            return data
        elif hasattr(data, "read"):
            return data.read()
        elif hasattr(data, "__iter__"):
            result = []
            for k, vs in to_key_val_list(data):
                iterable_vs: typing.Iterable[str | bytes | None]
                if isinstance(vs, (str, bytes, int, float, bool)) or not hasattr(vs, "__iter__"):
                    # not officially supported, but some people maybe passing ints, float, bool,
                    # or other string serializable classes.
                    if vs is not None and not isinstance(
                        vs,
                        (
                            str,
                            bytes,
                        ),
                    ):
                        iterable_vs = [str(vs)]
                    else:
                        iterable_vs = [vs]
                else:
                    iterable_vs = vs if vs is not None else []
                for v in iterable_vs:
                    if v is not None:
                        result.append(
                            (
                                k.encode("utf-8") if isinstance(k, str) else k,
                                v.encode("utf-8") if isinstance(v, str) else v,
                            )
                        )
            if boundary_for_multipart:
                return encode_multipart_formdata(
                    result,  # type: ignore[arg-type]
                    boundary=boundary_for_multipart,
                )[0]
            return urlencode(result, doseq=True)
        else:
            raise ValueError(f"Function _encode_params got an unexpected type argument '{type(data)}'")

    @staticmethod
    def _encode_files(
        files: MultiPartFilesType | MultiPartFilesAltType,
        data: dict[str | bytes, str | bytes] | list[tuple[str | bytes, str | bytes]] | None,
    ) -> tuple[bytes, str]:
        """Build the body for a multipart/form-data request.

        Will successfully encode files when passed as a dict or a list of
        tuples. Order is retained if data is a list of tuples but arbitrary
        if parameters are supplied as a dict.
        The tuples may be 2-tuples (filename, fileobj), 3-tuples (filename, fileobj, contentype)
        or 4-tuples (filename, fileobj, contentype, custom_headers).
        """
        if not files:
            raise ValueError("Files must be provided.")
        elif isinstance(data, str):
            raise ValueError("Data must not be a string.")

        new_fields: list[tuple[str, bytes] | RequestField] = []
        fields: list[tuple[str | bytes, str | bytes]] = to_key_val_list(data or {})
        no_dict_files: MultiPartFilesType = to_key_val_list(files or {})

        for field, val in fields:
            iterable_val: list[str | bytes]
            if isinstance(
                val,
                (
                    str,
                    bytes,
                ),
            ) or not hasattr(val, "__iter__"):
                iterable_val = [val]
            else:
                iterable_val = val
            for v in iterable_val:
                if v is not None:
                    # Don't call str() on bytestrings: in Py3 it all goes wrong.
                    if not isinstance(v, bytes):
                        v = str(v)

                    new_fields.append(
                        (
                            field.decode("utf-8") if isinstance(field, bytes) else field,
                            v.encode("utf-8") if isinstance(v, str) else v,
                        )
                    )

        for fkey, fdescriptor in no_dict_files:
            # support for explicit filename
            fn: str
            ft: str | None = None
            fh: HeadersType | None = None

            if isinstance(fdescriptor, (tuple, list)):
                # mypy and tuple length cmp not supported
                # https://github.com/python/mypy/issues/1178
                if len(fdescriptor) == 2:
                    fn, fp = tuple(fdescriptor)  # type: ignore[misc,assignment]
                elif len(fdescriptor) == 3:
                    fn, fp, ft = tuple(fdescriptor)  # type: ignore[misc,assignment]
                else:
                    fn, fp, ft, fh = tuple(fdescriptor)  # type: ignore[misc,assignment]
            else:
                if isinstance(fdescriptor, (str, bytes, bytearray)):
                    fn = fkey
                else:
                    fn = guess_filename(fdescriptor) or fkey

                fp = fdescriptor

            if isinstance(fp, (str, bytes, bytearray)):
                fdata = fp
            elif hasattr(fp, "read"):
                fdata = fp.read()
            elif fp is None:
                continue
            else:
                raise ValueError(f"Unexpected fp type given for multipart form data preparation: '{type(fp)}'")

            fh_converted: typing.MutableMapping[str, str] | None

            try:
                if fh:
                    if isinstance(fh, Headers):
                        fh = fh.to_dict()

                    fh_converted = dict()

                    for fh_key, fh_val in to_key_val_list(fh):
                        if isinstance(fh_key, bytes):
                            fh_key = fh_key.decode("ascii")
                        if isinstance(fh_val, bytes):
                            fh_val = fh_val.decode("latin-1")
                        fh_converted[fh_key] = fh_val
                else:
                    fh_converted = None
            except UnicodeDecodeError as e:
                raise ValueError("Tried to prepare a form data but failed due to non-decodable headers") from e

            rf = RequestField(name=fkey, data=fdata, filename=fn, headers=fh_converted)
            rf.make_multipart(content_type=ft)
            new_fields.append(rf)

        body, content_type = encode_multipart_formdata(new_fields)

        return body, content_type


class Response:
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.
    """

    __attrs__ = [
        "_content",
        "status_code",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
    ]

    __lazy_attrs__ = {
        "json",
        "ok",
        "links",
        "content",
        "text",
        "iter_lines",
        "iter_content",
        "next",
        "is_redirect",
        "is_permanent_redirect",
        "status_code",
        "cookies",
        "reason",
        "encoding",
        "url",
        "headers",
        "next",
        "_content",
        "status_code",
        "headers",
        "url",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
    }

    #: internals used for lazy responses. Do not try to access those unless you know what you are doing.
    #: they don't always exist.
    _promise: ResponsePromise
    _resolve_redirect: typing.Callable[[Response, PreparedRequest], PreparedRequest | None]

    def __init__(self) -> None:
        self._content: Literal[False] | bytes | None = False
        self._content_consumed: bool = False
        self._next: PreparedRequest | None = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code: int | None = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-encoding']`` will return the
        #: value of a ``'Content-Encoding'`` response header.
        self.headers: CaseInsensitiveDict = CaseInsensitiveDict()

        #: Case-insensitive Dictionary of Response Trailer Headers.
        #: This can only be filled after response consumption.
        self.trailers: CaseInsensitiveDict = CaseInsensitiveDict()

        #: File-like object representation of response (for advanced usage).
        #: Use of ``raw`` requires that ``stream=True`` be set on the request.
        #: This requirement does not apply for use internally to Requests.
        self.raw: BaseHTTPResponse | None = None

        #: Final URL location of Response.
        self.url: str | None = None

        #: Encoding to decode with when accessing r.text.
        self.encoding: str | None = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request. Any redirect responses will end
        #: up here. The list is sorted from the oldest to the most recent request.
        self.history: list[Response] = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason: str | None = None

        #: A CookieJar of Cookies the server sent back.
        self.cookies: CookieJar = cookiejar_from_dict({})

        #: The amount of time elapsed between sending the request
        #: and the arrival of the response (as a timedelta).
        #: This property specifically measures the time taken between sending
        #: the first byte of the request and finishing parsing the headers. It
        #: is therefore unaffected by consuming the response content or the
        #: value of the ``stream`` keyword argument.
        self.elapsed: datetime.timedelta = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request: PreparedRequest | None = None

        #: download progress if any. this property won't be set unless
        #: using stream=True + iter_content + content-length set!
        self.download_progress: TransferProgress | None = None

    @property
    def extension(
        self,
    ) -> (
        WebSocketExtensionFromHTTP
        | RawExtensionFromHTTP
        | ServerSideEventExtensionFromHTTP
        | AsyncWebSocketExtensionFromHTTP
        | AsyncRawExtensionFromHTTP
        | AsyncServerSideEventExtensionFromHTTP
        | None
    ):
        """Access the I/O after an Upgraded connection. E.g. for a WebSocket handler.
        If the server opened a WebSocket, then the extension will be of type WebSocketExtensionFromHTTP.
        Otherwise, on unknown protocol, it will be RawExtensionFromHTTP.
        Warning: If you stand in an async inclosure, the type
        will be AsyncWebSocketExtensionFromHTTP or AsyncRawExtensionFromHTTP."""
        return (
            self.raw.extension  # type: ignore[return-value]
            if self.raw is not None and hasattr(self.raw, "extension")
            else None
        )

    @property
    def lazy(self) -> bool:
        """
        Determine if response isn't received and is actually a placeholder.
        Only significant if request was sent through a multiplexed connection.
        """
        try:
            super().__getattribute__("_promise")
            return True
        except AttributeError:
            return False

    def _gather(self) -> None:
        """internals used for lazy responses. Do not try to access this unless you know what you are doing."""
        try:
            super().__getattribute__("_promise")
            super().__getattribute__("connection").gather(self)
        except AttributeError:
            pass

    def __getattribute__(self, item):
        try:
            if super().__getattribute__("raw") is None and item in Response.__lazy_attrs__ and super().__getattribute__("lazy"):
                if asyncio.iscoroutinefunction(super().__getattribute__("connection").gather):
                    raise MultiplexingError(
                        "Accessing a lazy response produced by an AsyncSession is forbidden. "
                        "Either call await session.gather() or set stream=True to produce an AsyncResponse "
                        "that you can access directly."
                    )
                else:
                    super().__getattribute__("_gather")()
        except AttributeError:
            pass

        return super().__getattribute__(item)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __getstate__(self):
        # Consume everything; accessing the content attribute makes
        # sure the content has been fully read.
        if self.lazy:
            if asyncio.iscoroutinefunction(super().__getattribute__("connection").gather):
                raise MultiplexingError(
                    "Accessing a lazy response produced by an AsyncSession is forbidden. "
                    "Either call await session.gather() or set stream=True to produce an AsyncResponse "
                    "that you can access directly."
                )
            else:
                self._gather()

        if not self._content_consumed:
            self.content

        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # pickled objects do not have .raw
        setattr(self, "_content_consumed", True)
        setattr(self, "raw", None)

        for name, value in state.items():
            setattr(self, name, value)

    def __repr__(self) -> str:
        if self.request is None or self.request.conn_info is None or self.request.conn_info.http_version is None:
            return f"<Response Dummy [{self.status_code}]>"

        # HTTP/2.0 is not preferred, cast it to HTTP/2 instead.
        http_revision = self.request.conn_info.http_version.value.replace(".0", "")

        if self.lazy:
            return f"<ResponsePromise {http_revision}>"

        return f"<Response {http_revision} [{self.status_code}]>"

    def __bool__(self) -> bool:
        """Returns True if :attr:`status_code` is less than 400.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code, is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        return self.ok

    def __iter__(self) -> typing.Generator[bytes, None, None]:
        """Allows you to use a response as an iterator."""
        return self.iter_content(ITER_CHUNK_SIZE)  # type: ignore[return-value]

    @property
    def ok(self) -> bool:
        """Returns True if :attr:`status_code` is less than 400, False if not.

        This attribute checks if the status code of the response is between
        400 and 600 to see if there was a client error or a server error. If
        the status code is between 200 and 400, this will return True. This
        is **not** a check to see if the response code is ``200 OK``.
        """
        try:
            self.raise_for_status()
        except HTTPError:
            return False
        return True

    @property
    def is_redirect(self) -> bool:
        """True if this Response is a well-formed HTTP redirect that could have
        been processed automatically (by :meth:`Session.resolve_redirects`).
        """
        return "location" in self.headers and self.status_code in REDIRECT_STATI

    @property
    def is_permanent_redirect(self) -> bool:
        """True if this Response one of the permanent versions of redirect."""
        return "location" in self.headers and self.status_code in (
            codes.moved_permanently,  # type: ignore[attr-defined]
            codes.permanent_redirect,  # type: ignore[attr-defined]
        )

    @property
    def next(self) -> PreparedRequest | None:
        """Returns a PreparedRequest for the next request in a redirect chain, if there is one."""
        return self._next

    @property
    def conn_info(self) -> ConnectionInfo | None:
        """Provide context to the established connection that was used to perform the request."""
        if self.request and hasattr(self.request, "conn_info"):
            return self.request.conn_info
        return None

    @property
    def ocsp_verified(self) -> bool | None:
        """Marker that can inform you of the OCSP verification."""
        if self.request and hasattr(self.request, "ocsp_verified"):
            return self.request.ocsp_verified
        return None

    @typing.overload
    def iter_content(
        self, chunk_size: int = ..., decode_unicode: Literal[False] = ...
    ) -> typing.Generator[bytes, None, None]: ...

    @typing.overload
    def iter_content(self, chunk_size: int = ..., *, decode_unicode: Literal[True]) -> typing.Generator[str, None, None]: ...

    def iter_content(
        self, chunk_size: int = ITER_CHUNK_SIZE, decode_unicode: bool = False
    ) -> typing.Generator[bytes | str, None, None]:
        """Iterates over the response data.  When stream=True is set on the
        request, this avoids reading the content at once into memory for
        large responses.  The chunk size is the number of bytes it should
        read into memory.  This is not necessarily the length of each item
        returned as decoding can take place.

        chunk_size must be of type int or None. A value of None will
        function differently depending on the value of `stream`.
        stream=True will read data as it arrives in whatever size the
        chunks are received. If stream=False, data is returned as
        a single chunk.

        If decode_unicode is True, content will be decoded using the best
        available encoding based on the response.

        We recommend setting chunk_size=-1 (default) to receive chunk as they come
        for performance purposes.
        """

        def generate() -> typing.Generator[bytes, None, None]:
            assert self.raw is not None

            can_track_progress = hasattr(self.raw, "_fp") and hasattr(self.raw._fp, "data_in_count")

            if can_track_progress and self.download_progress is None:
                if "content-length" in self.headers:
                    self.download_progress = TransferProgress()
                    try:
                        self.download_progress.content_length = int(self.headers["content-length"])
                    except ValueError:
                        pass
            # Special case for urllib3.
            if hasattr(self.raw, "stream"):
                try:
                    for chunk in self.raw.stream(chunk_size, decode_content=True):
                        if self.download_progress is not None:
                            self.download_progress.total = self.raw._fp.data_in_count  # type: ignore[union-attr]
                        yield chunk
                except ProtocolError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ConnectionError(e)
                except SSLError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise RequestsSSLError(e)
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            if self.raw is not None and hasattr(self.raw, "trailers"):
                self.trailers = CaseInsensitiveDict(self.raw.trailers)

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(f"chunk_size must be an int, it is instead a {type(chunk_size)}.")
        # simulate reading small chunks of the content
        reused_chunks = iter_slices(self._content or b"", chunk_size)

        stream_chunks = generate()

        chunks = reused_chunks if self._content_consumed else stream_chunks

        if decode_unicode:
            return stream_decode_response_unicode(chunks, self)

        return chunks

    def iter_raw(self, chunk_size: int = ITER_CHUNK_SIZE) -> typing.Generator[bytes, None, None]:
        """Iterates over the response raw and possibly compressed data.
        When stream=True is set on the request, this avoids
        reading the content at once into memory for
        large responses. The chunk size is the number of bytes it should
        read into memory. This is not necessarily the length of each item
        returned as decoding can take place.

        chunk_size must be of type int or None. A value of None will
        function differently depending on the value of `stream`.
        stream=True will read data as it arrives in whatever size the
        chunks are received. If stream=False, data is returned as
        a single chunk.

        If decode_unicode is True, content will be decoded using the best
        available encoding based on the response.

        We recommend setting chunk_size=-1 (default) to receive chunk as they come
        for performance purposes.
        """

        def generate() -> typing.Generator[bytes, None, None]:
            assert self.raw is not None

            can_track_progress = hasattr(self.raw, "_fp") and hasattr(self.raw._fp, "data_in_count")

            if can_track_progress and self.download_progress is None:
                if "content-length" in self.headers:
                    self.download_progress = TransferProgress()
                    try:
                        self.download_progress.content_length = int(self.headers["content-length"])
                    except ValueError:
                        pass
            # Special case for urllib3.
            if hasattr(self.raw, "stream"):
                try:
                    for chunk in self.raw.stream(chunk_size, decode_content=False):
                        if self.download_progress is not None:
                            self.download_progress.total = self.raw._fp.data_in_count  # type: ignore[union-attr]
                        yield chunk
                except ProtocolError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise ConnectionError(e)
                except SSLError as e:
                    if self.download_progress is not None:
                        self.download_progress.any_error = True
                    raise RequestsSSLError(e)
            else:
                # Standard file-like object.
                while True:
                    chunk = self.raw.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            if self.raw is not None and hasattr(self.raw, "trailers"):
                self.trailers = CaseInsensitiveDict(self.raw.trailers)

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(f"chunk_size must be an int, it is instead a {type(chunk_size)}.")
        # simulate reading small chunks of the content
        reused_chunks = iter_slices(self._content or b"", chunk_size)

        return reused_chunks if self._content_consumed else generate()

    @typing.overload
    def iter_lines(
        self,
        chunk_size: int = ...,
        decode_unicode: Literal[False] = ...,
        delimiter: str | bytes | None = ...,
    ) -> typing.Generator[bytes, None, None]: ...

    @typing.overload
    def iter_lines(
        self,
        chunk_size: int = ...,
        *,
        decode_unicode: Literal[True],
        delimiter: str | bytes | None = ...,
    ) -> typing.Generator[str, None, None]: ...

    def iter_lines(
        self,
        chunk_size: int = ITER_CHUNK_SIZE,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> typing.Generator[bytes | str, None, None]:
        """Iterates over the response data, one line at a time.  When
        stream=True is set on the request, this avoids reading the
        content at once into memory for large responses.

        .. note:: This method is not reentrant safe.
        """
        if delimiter is not None and decode_unicode is False and isinstance(delimiter, str):
            raise ValueError(
                "delimiter MUST match the desired output type. e.g. "
                "if decode_unicode is set to True, delimiter MUST be a str, otherwise we expect a bytes-like variable."
            )

        pending = None

        for chunk in self.iter_content(  # type: ignore[call-overload]
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)  # type: ignore[arg-type]
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            yield from lines

        if pending is not None:
            yield pending

    @property
    def oheaders(self) -> Headers:
        """
        Retrieve headers as they were objects. There is no need to parse headers yourself.
        A simple Mapping isn't enough to quickly access and analyze them.
        Read the full documentation of object-oriented headers at https://jawah.github.io/kiss-headers/
        >>> import niquests
        >>> r = niquests.get("https://google.com")
        >>> r.oheaders.content_type.charset
        'ISO-8859-1'
        >>> r.oheaders.content_type
        'text/html; charset=ISO-8859-1'
        >>> r.oheaders.content_type[0]
        'text/html'
        """
        if self.raw:
            headers = parse_it(self.raw)
            headers -= "Set-Cookie"
            return headers
        return parse_it(self.headers)

    @property
    def otrailers(self) -> Headers:
        """
        Retrieve trailers as they were objects. There is no need to parse headers yourself.
        """
        if self.raw:
            return parse_it(self.raw.trailers)
        return parse_it(self.trailers)

    @property
    def content(self) -> bytes | None:
        """Content of the response, in bytes."""

        if self._content is False:
            # Read the contents.
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0 or self.raw is None:
                self._content = None
            else:
                try:
                    if hasattr(self.raw, "stream"):
                        self._content = self.raw.read(decode_content=True)  # type: ignore[arg-type]
                    else:
                        self._content = self.raw.read()
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)

        self._content_consumed = True
        if self.raw is not None and hasattr(self.raw, "trailers"):
            self.trailers = CaseInsensitiveDict(self.raw.trailers)
        # don't need to release the connection; that's been handled by urllib3
        # since we exhausted the data.
        return self._content  # type: ignore[return-value]

    @property
    def text(self) -> str | None:
        """Content of the response, in unicode.

        If Response.encoding is None, encoding will be guessed using
        ``charset_normalizer``.

        The encoding of the response content is determined based solely on HTTP
        headers, following RFC 2616 to the letter. If you can take advantage of
        non-HTTP knowledge to make a better guess at the encoding, you should
        set ``r.encoding`` appropriately before accessing this property.
        """
        if not self.content:
            return ""

        if self.encoding is not None:
            try:
                info = codecs.lookup(self.encoding)

                if hasattr(info, "_is_text_encoding") and info._is_text_encoding is False:
                    return None
            except LookupError:
                #: We cannot accept unsupported or nonexistent encoding. Override.
                self.encoding = None

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding_guess = from_bytes(self.content).best()

            if encoding_guess:
                #: We shall cache this inference.
                self.encoding = encoding_guess.encoding
                return str(encoding_guess)

        if self.encoding is None:
            return None

        return str(self.content, self.encoding, errors="replace")

    def json(self, **kwargs: typing.Any) -> typing.Any:
        r"""Returns the json-encoded content of a response, if any.

        :param \*\*kwargs: Optional arguments that ``json.loads`` takes.
        :raises requests.exceptions.JSONDecodeError: If the response body does not
            contain valid json or if content-type is not about json.
        """

        if not self.content:
            raise RequestsJSONDecodeError("response content is not JSON", "", 0)

        if not self.encoding:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding_guess = from_bytes(
                self.content,
                cp_isolation=[
                    "ascii",
                    "utf-8",
                    "utf-16",
                    "utf-32",
                    "utf-16-le",
                    "utf-16-be",
                    "utf-32-le",
                    "utf-32-be",
                ],
            ).best()

            if encoding_guess is not None:
                self.encoding = encoding_guess.encoding
                try:
                    return _json.loads(str(encoding_guess), **kwargs)
                except _json.JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
            else:
                self.encoding = "utf-8"  # try Unicode anyway[...]

        plain_content = self.text

        if plain_content is None:
            raise RequestsJSONDecodeError("response cannot lead to decodable JSON", "", 0)

        try:
            return _json.loads(plain_content, **kwargs)
        except _json.JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    @property
    def links(self):
        """Returns the parsed header links of the response, if any."""

        header = self.headers.get("link")

        resolved_links = {}

        if header:
            links = parse_header_links(header)

            for link in links:
                key = link.get("rel") or link.get("url")
                resolved_links[key] = link

        return resolved_links

    @property
    def http_version(self) -> int | None:
        """Shortcut to negotiated HTTP version protocol. See HttpVersion from urllib3.future.
        It returns an integer. It is as follows:

        - 11 for HTTP/1.1
        - 20 for HTTP/2
        - 30 for HTTP/3
        """
        return self.raw.version if self.raw else None

    def raise_for_status(self) -> Response:
        """Raises :class:`HTTPError`, if one occurred."""

        if self.status_code is None:
            return self

        http_error_msg = ""
        if isinstance(self.reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings. (See PR #3538)
            try:
                reason = self.reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = self.reason.decode("iso-8859-1")
        else:
            reason = self.reason

        if 400 <= self.status_code < 500:
            http_error_msg = f"{self.status_code} Client Error: {reason} for url: {self.url}"

        elif 500 <= self.status_code < 600:
            http_error_msg = f"{self.status_code} Server Error: {reason} for url: {self.url}"

        if http_error_msg:
            raise HTTPError(http_error_msg, response=self)

        return self

    def close(self) -> None:
        """Releases the connection back to the pool. Once this method has been
        called the underlying ``raw`` object must not be accessed again.

        *Note: Should not normally need to be called explicitly.*
        """
        if self._content_consumed is False and self.raw is not None:
            if not asyncio.iscoroutinefunction(self.raw.close):
                self.raw.close()
            else:
                warnings.warn(
                    "use 'async with response' to be able to cleanly close the response in async mode.",
                    UserWarning,
                )

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()

    async def __aenter__(self) -> Response:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._content_consumed is False and self.raw is not None:
            if not asyncio.iscoroutinefunction(self.raw.close):
                raise OSError("Attempted to use a synchronous response in an awaitable context.")

            await self.raw.close()

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()


class AsyncResponse(Response):
    raw: BaseAsyncHTTPResponse | None
    _resolve_redirect: typing.Callable[  # type: ignore[assignment]
        [Response, PreparedRequest], typing.Awaitable[PreparedRequest | None]
    ]

    __lazy_attrs__ = {
        "ok",
        "links",
        "next",
        "is_redirect",
        "is_permanent_redirect",
        "status_code",
        "cookies",
        "reason",
        "encoding",
        "url",
        "headers",
        "next",
        "_content",
        "status_code",
        "headers",
        "url",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
    }

    @property
    def extension(  # type: ignore[override]
        self,
    ) -> AsyncWebSocketExtensionFromHTTP | AsyncRawExtensionFromHTTP | None:
        """Access the I/O after an Upgraded connection. E.g. for a WebSocket handler.
        If the server opened a WebSocket, then the extension will be of type AsyncWebSocketExtensionFromHTTP.
        Otherwise, on unknown protocol, it will be AsyncRawExtensionFromHTTP."""
        return (
            self.raw.extension  # type: ignore[return-value]
            if self.raw is not None and hasattr(self.raw, "extension")
            else None
        )

    def __aenter__(self) -> AsyncResponse:  # type: ignore[override]
        return self

    async def __aiter__(self) -> typing.AsyncIterator[bytes]:
        async for chunk in await self.iter_content(ITER_CHUNK_SIZE):
            yield chunk

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def __getattribute__(self, item):
        if item in AsyncResponse.__lazy_attrs__ and self.lazy:
            raise MultiplexingError(
                "Accessing a lazy async response produced by an AsyncSession is forbidden this way. "
                "Either call await session.gather() or await one of (text, json, content, iter_content, iter_line, etc..) "
                "that are awaitable."
            )
        return super(Response, self).__getattribute__(item)

    async def _gather(self) -> None:  # type: ignore[override]
        """internals used for lazy responses. Do not try to access this unless you know what you are doing."""
        if hasattr(self, "_promise") and hasattr(self, "connection"):
            await self.connection.gather(self)

    @typing.overload  # type: ignore[override]
    async def iter_content(
        self, chunk_size: int = ..., decode_unicode: Literal[False] = ...
    ) -> typing.AsyncGenerator[bytes, None]: ...

    @typing.overload  # type: ignore[override]
    async def iter_content(
        self, chunk_size: int = ..., *, decode_unicode: Literal[True]
    ) -> typing.AsyncGenerator[str, None]: ...

    async def iter_content(  # type: ignore[override]
        self, chunk_size: int = ITER_CHUNK_SIZE, decode_unicode: bool = False
    ) -> typing.AsyncGenerator[bytes | str, None]:
        if self.lazy:
            await self._gather()

        async def generate() -> typing.AsyncGenerator[
            bytes,
            None,
        ]:
            assert self.raw is not None

            can_track_progress = hasattr(self.raw, "_fp") and hasattr(self.raw._fp, "data_in_count")

            if can_track_progress and self.download_progress is None:
                if "content-length" in self.headers:
                    self.download_progress = TransferProgress()
                    try:
                        self.download_progress.content_length = int(self.headers["content-length"])
                    except ValueError:
                        pass

            while True:
                try:
                    chunk = await self.raw.read(chunk_size, decode_content=True)

                    if self.download_progress is not None:
                        self.download_progress.total = self.raw._fp.data_in_count  # type: ignore[union-attr]
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)

                if not chunk:
                    break

                yield chunk

            if self.raw is not None and hasattr(self.raw, "trailers"):
                self.trailers = CaseInsensitiveDict(self.raw.trailers)

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(f"chunk_size must be an int, it is instead a {type(chunk_size)}.")

        stream_chunks = generate()

        if decode_unicode:
            return astream_decode_response_unicode(stream_chunks, self)

        return stream_chunks

    async def iter_raw(  # type: ignore[override]
        self, chunk_size: int = ITER_CHUNK_SIZE
    ) -> typing.AsyncGenerator[bytes, None]:
        if self.lazy:
            await self._gather()

        async def generate() -> typing.AsyncGenerator[
            bytes,
            None,
        ]:
            assert self.raw is not None

            can_track_progress = hasattr(self.raw, "_fp") and hasattr(self.raw._fp, "data_in_count")

            if can_track_progress and self.download_progress is None:
                if "content-length" in self.headers:
                    self.download_progress = TransferProgress()
                    try:
                        self.download_progress.content_length = int(self.headers["content-length"])
                    except ValueError:
                        pass

            while True:
                try:
                    chunk = await self.raw.read(chunk_size, decode_content=False)

                    if self.download_progress is not None:
                        self.download_progress.total = self.raw._fp.data_in_count  # type: ignore[union-attr]
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)

                if not chunk:
                    break

                yield chunk

            if self.raw is not None and hasattr(self.raw, "trailers"):
                self.trailers = CaseInsensitiveDict(self.raw.trailers)

            self._content_consumed = True

        if self._content_consumed and isinstance(self._content, bool):
            raise StreamConsumedError()
        elif chunk_size is not None and not isinstance(chunk_size, int):
            raise TypeError(f"chunk_size must be an int, it is instead a {type(chunk_size)}.")

        return generate()

    @typing.overload  # type: ignore[override]
    async def iter_lines(
        self,
        chunk_size: int = ...,
        decode_unicode: Literal[False] = ...,
        delimiter: str | bytes | None = ...,
    ) -> typing.AsyncGenerator[bytes, None]: ...

    @typing.overload  # type: ignore[override]
    async def iter_lines(
        self,
        chunk_size: int = ...,
        *,
        decode_unicode: Literal[True],
        delimiter: str | bytes | None = ...,
    ) -> typing.AsyncGenerator[str, None]: ...

    async def iter_lines(  # type: ignore[misc]
        self,
        chunk_size: int = ITER_CHUNK_SIZE,
        decode_unicode: bool = False,
        delimiter: str | bytes | None = None,
    ) -> typing.AsyncGenerator[bytes | str, None]:
        if delimiter is not None and decode_unicode is False and isinstance(delimiter, str):
            raise ValueError(
                "delimiter MUST match the desired output type. e.g. "
                "if decode_unicode is set to True, delimiter MUST be a str, otherwise we expect a bytes-like variable."
            )

        pending = None

        async for chunk in await self.iter_content(  # type: ignore[call-overload]
            chunk_size=chunk_size, decode_unicode=decode_unicode
        ):
            if pending is not None:
                chunk = pending + chunk

            if delimiter:
                lines = chunk.split(delimiter)  # type: ignore[arg-type]
            else:
                lines = chunk.splitlines()

            if lines and lines[-1] and chunk and lines[-1][-1] == chunk[-1]:
                pending = lines.pop()
            else:
                pending = None

            for line in lines:
                yield line

        if pending is not None:
            yield pending

    @property
    async def content(self) -> bytes | None:  # type: ignore[override]
        if self.lazy:
            await self._gather()

        if self._content is False:
            # Read the contents.
            if self._content_consumed:
                raise RuntimeError("The content for this response was already consumed")

            if self.status_code == 0 or self.raw is None:
                self._content = None
            else:
                try:
                    if isinstance(self.raw, BaseAsyncHTTPResponse):
                        self._content = await self.raw.read(decode_content=True)  # type: ignore[arg-type]
                    else:
                        raise OSError
                except ProtocolError as e:
                    raise ChunkedEncodingError(e)
                except DecodeError as e:
                    raise ContentDecodingError(e)
                except ReadTimeoutError as e:
                    raise ConnectionError(e)
                except SSLError as e:
                    raise RequestsSSLError(e)

        if self.raw is not None and hasattr(self.raw, "trailers"):
            self.trailers = CaseInsensitiveDict(self.raw.trailers)

        self._content_consumed = True
        # don't need to release the connection; that's been handled by urllib3
        # since we exhausted the data.
        return self._content  # type: ignore[return-value]

    @property
    async def text(self) -> str | None:  # type: ignore[override]
        content = await self.content

        if not content:
            return ""

        if self.encoding is not None:
            try:
                info = codecs.lookup(self.encoding)

                if hasattr(info, "_is_text_encoding") and info._is_text_encoding is False:
                    return None
            except LookupError:
                #: We cannot accept unsupported or nonexistent encoding. Override.
                self.encoding = None

        # Fallback to auto-detected encoding.
        if self.encoding is None:
            encoding_guess = from_bytes(content).best()

            if encoding_guess:
                #: We shall cache this inference.
                self.encoding = encoding_guess.encoding
                return str(encoding_guess)

        if self.encoding is None:
            return None

        return str(content, self.encoding, errors="replace")

    async def json(self, **kwargs: typing.Any) -> typing.Any:  # type: ignore[override]
        content = await self.content

        if not content:
            raise RequestsJSONDecodeError("response content is not JSON", "", 0)

        if not self.encoding:
            # No encoding set. JSON RFC 4627 section 3 states we should expect
            # UTF-8, -16 or -32. Detect which one to use; If the detection or
            # decoding fails, fall back to `self.text` (using charset_normalizer to make
            # a best guess).
            encoding_guess = from_bytes(
                content,
                cp_isolation=[
                    "ascii",
                    "utf-8",
                    "utf-16",
                    "utf-32",
                    "utf-16-le",
                    "utf-16-be",
                    "utf-32-le",
                    "utf-32-be",
                ],
            ).best()

            if encoding_guess is not None:
                self.encoding = encoding_guess.encoding
                try:
                    return _json.loads(str(encoding_guess), **kwargs)
                except _json.JSONDecodeError as e:
                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
            else:
                self.encoding = "utf-8"

        plain_content = await self.text

        if plain_content is None:
            raise RequestsJSONDecodeError("response cannot lead to unserializable JSON", "", 0)

        try:
            return _json.loads(plain_content, **kwargs)
        except _json.JSONDecodeError as e:
            # Catch JSON-related errors and raise as requests.JSONDecodeError
            # This aliases json.JSONDecodeError and simplejson.JSONDecodeError
            raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)

    async def close(self) -> None:  # type: ignore[override]
        if self.lazy:
            await self._gather()

        if self._content_consumed is False and self.raw is not None:
            await self.raw.close()

        release_conn = getattr(self.raw, "release_conn", None)
        if release_conn is not None:
            release_conn()

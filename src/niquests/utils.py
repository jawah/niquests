"""
requests.utils
~~~~~~~~~~~~~~

This module provides utility functions that are used within Requests
that are also useful for external consumption.
"""

from __future__ import annotations

import codecs
import contextlib
import io
import os
import re
import socket
import struct
import sys
import tempfile
import typing
from collections import OrderedDict
from functools import lru_cache
from http.cookiejar import CookieJar
from netrc import NetrcParseError, netrc
from urllib.parse import quote, unquote, urlparse, urlunparse
from urllib.request import (  # type: ignore[attr-defined]  # type: ignore[attr-defined]
    getproxies,
    getproxies_environment,
    proxy_bypass,
    proxy_bypass_environment,
)
from urllib.request import parse_http_list as _parse_list_header

import wassima

from .__version__ import __version__
from .exceptions import InvalidURL, MissingSchema, UnrewindableBodyError
from .packages.urllib3 import ConnectionInfo
from .packages.urllib3.contrib.resolver import (
    BaseResolver,
    ManyResolver,
    ProtocolResolver,
    ResolverDescription,
)
from .packages.urllib3.contrib.resolver._async import (
    AsyncBaseResolver,
    AsyncManyResolver,
    AsyncResolverDescription,
)
from .packages.urllib3.contrib.webextensions import ExtensionFromHTTP, load_extension
from .packages.urllib3.contrib.webextensions._async import AsyncExtensionFromHTTP
from .packages.urllib3.util import make_headers, parse_url
from .structures import CaseInsensitiveDict

if typing.TYPE_CHECKING:
    from ._typing import AsyncResolverType, ResolverType
    from .cookies import RequestsCookieJar
    from .models import AsyncResponse, PreparedRequest, Request, Response


getproxies = lru_cache()(getproxies)
getproxies_environment = lru_cache()(getproxies_environment)

NETRC_FILES = (".netrc", "_netrc")

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443}

# Ensure that ', ' is used to preserve previous delimiter behavior.
DEFAULT_ACCEPT_ENCODING: str = ", ".join(re.split(r",\s*", make_headers(accept_encoding=True)["accept-encoding"]))


if sys.platform == "win32":
    # provide a proxy_bypass version on Windows without DNS lookups

    def proxy_bypass_registry(host) -> bool:
        try:
            import winreg
        except ImportError:
            return False

        try:
            internetSettings = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            # ProxyEnable could be REG_SZ or REG_DWORD, normalizing it
            proxyEnable = int(winreg.QueryValueEx(internetSettings, "ProxyEnable")[0])
            # ProxyOverride is almost always a string
            proxyOverride = winreg.QueryValueEx(internetSettings, "ProxyOverride")[0]
        except (OSError, ValueError):
            return False
        if not proxyEnable or not proxyOverride:
            return False

        # make a check value list from the registry entry: replace the
        # '<local>' string by the localhost entry and the corresponding
        # canonical entry.
        proxyOverride = proxyOverride.split(";")
        # Sometime empty value can land in evaluated proxyOverride.split(";").
        # We clear them out before doing any regexp match.
        proxyOverride = filter(None, proxyOverride)
        # now check if we match one of the registry values.
        for test in proxyOverride:
            if test == "<local>":
                if "." not in host:
                    return True
            test = test.replace(".", r"\.")  # mask dots
            test = test.replace("*", r".*")  # change glob sequence
            test = test.replace("?", r".")  # change glob char
            if re.match(test, host, re.I):
                return True
        return False

    def proxy_bypass(host: str) -> bool:  # noqa
        """Return True, if the host should be bypassed.

        Checks proxy settings gathered from the environment, if specified,
        or the registry.
        """
        if getproxies_environment():
            return proxy_bypass_environment(host)
        else:
            return proxy_bypass_registry(host)


def super_len(o: typing.Any) -> int:
    total_length = None
    current_position = 0

    if hasattr(o, "__len__"):
        total_length = len(o)

    elif hasattr(o, "len"):
        total_length = o.len

    elif hasattr(o, "fileno"):
        try:
            fileno = o.fileno()
        except (io.UnsupportedOperation, AttributeError):
            # AttributeError is a surprising exception, seeing as how we've just checked
            # that `hasattr(o, 'fileno')`.  It happens for objects obtained via
            # `Tarfile.extractfile()`, per issue 5229.
            pass
        else:
            total_length = os.fstat(fileno).st_size

    if hasattr(o, "tell"):
        try:
            current_position = o.tell()
        except OSError:
            # This can happen in some weird situations, such as when the file
            # is actually a special file descriptor like stdin. In this
            # instance, we don't know what the length is, so set it to zero and
            # let requests chunk it instead.
            if total_length is not None:
                current_position = total_length
        else:
            if hasattr(o, "seek") and total_length is None:
                # StringIO and BytesIO have seek but no usable fileno
                try:
                    # seek to end of file
                    o.seek(0, 2)
                    total_length = o.tell()

                    # seek back to current position to support
                    # partially read file-like objects
                    o.seek(current_position or 0)
                except OSError:
                    total_length = 0

    if total_length is None:
        total_length = 0

    return max(0, total_length - current_position)


@lru_cache(maxsize=64)
def get_netrc_auth(url: str | None, raise_errors: bool = False) -> tuple[str, str] | None:
    """Returns the Requests tuple auth for a given url from netrc."""

    if url is None:
        return None

    netrc_file = os.environ.get("NETRC")
    netrc_locations: tuple[str, ...] = (netrc_file,) if netrc_file is not None else tuple(f"~/{f}" for f in NETRC_FILES)

    try:
        netrc_path = next(
            (os.path.expanduser(f) for f in netrc_locations if os.path.exists(os.path.expanduser(f))),
            None,
        )
        if netrc_path is None:
            return None

        ri = parse_url(url)
        host = ri.hostname

        if host is None:
            return None

        _netrc = netrc(netrc_path).authenticators(host)

        if _netrc:
            login, _, password = _netrc
            if login and password:
                return login, password
            return None
    except NetrcParseError as e:
        if raise_errors:
            raise ValueError("Syntax error in netrc file") from e
    except OSError as e:
        if raise_errors:
            raise OSError("Problem accessing or reading the netrc file") from e
    except AttributeError as e:
        if raise_errors:
            raise RuntimeError("Unexpected error while retrieving netrc authenticators") from e
    return None


def guess_filename(obj: typing.IO) -> str | None:
    """Tries to guess the filename of the given object."""
    name = getattr(obj, "name", None)
    if name and isinstance(name, str) and name[0] != "<" and name[-1] != ">":
        return os.path.basename(name)
    return None


@contextlib.contextmanager
def atomic_open(
    filename: str | bytes | os.PathLike,
) -> typing.Generator[typing.BinaryIO, None, None]:
    """Write a file to the disk in an atomic fashion"""
    tmp_descriptor, tmp_name = tempfile.mkstemp(dir=os.path.dirname(filename))
    try:
        with os.fdopen(tmp_descriptor, "wb") as tmp_handler:
            yield tmp_handler
        os.replace(tmp_name, filename)
    except BaseException:
        os.remove(tmp_name)
        raise


def from_key_val_list(value: typing.Any | None) -> OrderedDict | None:
    """Take an object and test to see if it can be represented as a
    dictionary. Unless it can not be represented as such, return an
    OrderedDict, e.g.,

    ::

        >>> from_key_val_list([('key', 'val')])
        OrderedDict([('key', 'val')])
        >>> from_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples
        >>> from_key_val_list({'key': 'val'})
        OrderedDict([('key', 'val')])
    """
    if value is None:
        return None

    if not isinstance(value, (tuple, list, dict)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    return OrderedDict(value)


_KT = typing.TypeVar("_KT")
_VT = typing.TypeVar("_VT")


def to_key_val_list(
    value: dict[_KT, _VT] | typing.Mapping[_KT, _VT] | typing.Iterable[tuple[_KT, _VT]],
) -> list[tuple[_KT, _VT]]:
    """Take an object and test to see if it can be represented as a
    dictionary. If it can be, return a list of tuples, e.g.,

    ::

        >>> to_key_val_list([('key', 'val')])
        [('key', 'val')]
        >>> to_key_val_list({'key': 'val'})
        [('key', 'val')]
        >>> to_key_val_list('string')
        Traceback (most recent call last):
        ...
        ValueError: cannot encode objects that are not 2-tuples
    """
    if value is None:
        raise ValueError("cannot accept None in to_key_val_list")

    if isinstance(value, (str, bytes, bool, int)):
        raise ValueError("cannot encode objects that are not 2-tuples")

    if hasattr(value, "items"):
        value = value.items()

    return list(value)


# From mitsuhiko/werkzeug (used with permission).
def parse_list_header(value: str) -> list[str]:
    """Parse lists as described by RFC 2068 Section 2.

    In particular, parse comma-separated lists where the elements of
    the list may include quoted-strings.  A quoted-string could
    contain a comma.  A non-quoted string could have quotes in the
    middle.  Quotes are removed automatically after parsing.

    It basically works like :func:`parse_set_header` just that items
    may appear multiple times and case sensitivity is preserved.

    The return value is a standard :class:`list`:

    >>> parse_list_header('token, "quoted value"')
    ['token', 'quoted value']

    To create a header from the :class:`list` again, use the
    :func:`dump_header` function.

    :param value: a string with a list header.
    :return: :class:`list`
    """
    result = []
    for item in _parse_list_header(value):
        if item[:1] == item[-1:] == '"':
            item = unquote_header_value(item[1:-1])
        result.append(item)
    return result


# From mitsuhiko/werkzeug (used with permission).
def parse_dict_header(value: str) -> typing.Mapping[str, str | None]:
    """Parse lists of key, value pairs as described by RFC 2068 Section 2 and
    convert them into a python dict:

    >>> d = parse_dict_header('foo="is a fish", bar="as well"')
    >>> type(d) is dict
    True
    >>> sorted(d.items())
    [('bar', 'as well'), ('foo', 'is a fish')]

    If there is no value for a key it will be `None`:

    >>> parse_dict_header('key_without_value')
    {'key_without_value': None}

    To create a header from the :class:`dict` again, use the
    :func:`dump_header` function.

    :param value: a string with a dict header.
    :return: :class:`dict`
    """
    result: typing.MutableMapping[str, str | None] = {}
    for item in _parse_list_header(value):
        if "=" not in item:
            result[item] = None
            continue
        name, value = item.split("=", 1)
        if value[:1] == value[-1:] == '"':
            value = unquote_header_value(value[1:-1])
        result[name] = value
    return result


# From mitsuhiko/werkzeug (used with permission).
def unquote_header_value(value: str, is_filename: bool = False) -> str:
    r"""Unquotes a header value.  (Reversal of :func:`quote_header_value`).
    This does not use the real unquoting but what browsers are actually
    using for quoting.

    :param value: the header value to unquote.
    """
    if value and value[0] == value[-1] == '"':
        # this is not the real unquoting, but fixing this so that the
        # RFC is met will result in bugs with internet explorer and
        # probably some other browsers as well.  IE for example is
        # uploading files with "C:\foo\bar.txt" as filename
        value = value[1:-1]

        # if this is a filename and the starting characters look like
        # a UNC path, then just return the value without quotes.  Using the
        # replace sequence below on a UNC path has the effect of turning
        # the leading double slash into a single slash and then
        # _fix_ie_filename() doesn't work correctly.  See #458.
        if not is_filename or value[:2] != "\\\\":
            return value.replace("\\\\", "\\").replace('\\"', '"')
    return value


def dict_from_cookiejar(cj: CookieJar) -> dict[str, str | None]:
    """Returns a key/value dictionary from a CookieJar.

    :param cj: CookieJar object to extract cookies from.
    """

    cookie_dict = {cookie.name: cookie.value for cookie in cj}
    return cookie_dict


def add_dict_to_cookiejar(cj: RequestsCookieJar, cookie_dict) -> RequestsCookieJar | CookieJar:
    """Returns a CookieJar from a key/value dictionary.

    :param cj: CookieJar to insert cookies into.
    :param cookie_dict: Dict of key/values to insert into CookieJar.
    """
    from .cookies import cookiejar_from_dict

    return cookiejar_from_dict(cookie_dict, cj)


def _parse_content_type_header(
    header: str,
) -> tuple[str, dict[str, str | typing.Literal[True]]]:
    """Returns content type and parameters from given header

    :param header: string
    :return: tuple containing content type and dictionary of
         parameters
    """

    tokens = header.split(";")
    content_type, params = tokens[0].strip(), tokens[1:]
    params_dict = {}
    items_to_strip = "\"' "

    for param in params:
        param = param.strip()
        if param:
            value: typing.Literal[True] | str

            key, value = param, True
            index_of_equals = param.find("=")
            if index_of_equals != -1:
                key = param[:index_of_equals].strip(items_to_strip)
                value = param[index_of_equals + 1 :].strip(items_to_strip)
            params_dict[key.lower()] = value
    return content_type, params_dict


def get_encoding_from_headers(headers: typing.Mapping[str, str]) -> str | None:
    """Returns encodings from given HTTP Header Dict.

    :param headers: dictionary to extract encoding from.
    """

    content_type = headers.get("content-type")

    if not content_type:
        return None

    content_type, params = _parse_content_type_header(content_type)

    if "charset" in params:
        return params["charset"].strip("'\"") if isinstance(params["charset"], str) else None

    if "application/json" in content_type:
        # Assume UTF-8 based on RFC 4627: https://www.ietf.org/rfc/rfc4627.txt since the charset was unset
        return "utf-8"

    return None


def stream_decode_response_unicode(
    iterator: typing.Generator[bytes, None, None], r: Response
) -> typing.Generator[bytes | str, None, None]:
    """Stream decodes an iterator."""

    if r.encoding is None:
        yield from iterator
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")
    for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv


async def astream_decode_response_unicode(
    iterator: typing.AsyncGenerator[bytes, None], r: Response
) -> typing.AsyncGenerator[bytes | str, None]:
    """Stream decodes an iterator."""

    if r.encoding is None:
        async for chunk in iterator:
            yield chunk
        return

    decoder = codecs.getincrementaldecoder(r.encoding)(errors="replace")

    async for chunk in iterator:
        rv = decoder.decode(chunk)
        if rv:
            yield rv
    rv = decoder.decode(b"", final=True)
    if rv:
        yield rv


_SV = typing.TypeVar("_SV", str, bytes)


def iter_slices(string: _SV, slice_length: int | None) -> typing.Generator[_SV, None, None]:
    """Iterate over slices of a string."""
    pos = 0
    if slice_length is None or slice_length <= 0:
        slice_length = len(string)
    while pos < len(string):
        yield string[pos : pos + slice_length]
        pos += slice_length


# The unreserved URI characters (RFC 3986)
UNRESERVED_SET = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" + "0123456789-._~")


def unquote_unreserved(uri: str) -> str:
    """Un-escape any percent-escape sequences in a URI that are unreserved
    characters. This leaves all reserved, illegal and non-ASCII bytes encoded.
    """
    parts = uri.split("%")
    for i in range(1, len(parts)):
        h = parts[i][0:2]
        if len(h) == 2 and h.isalnum():
            try:
                c = chr(int(h, 16))
            except ValueError:
                raise InvalidURL(f"Invalid percent-escape sequence: '{h}'")

            if c in UNRESERVED_SET:
                parts[i] = c + parts[i][2:]
            else:
                parts[i] = f"%{parts[i]}"
        else:
            parts[i] = f"%{parts[i]}"
    return "".join(parts)


def requote_uri(uri: str) -> str:
    """Re-quote the given URI.

    This function passes the given URI through an unquote/quote cycle to
    ensure that it is fully and consistently quoted.
    """
    safe_with_percent = "!#$%&'()*+,/:;=?@[]~"
    safe_without_percent = "!#$&'()*+,/:;=?@[]~"
    try:
        # Unquote only the unreserved characters
        # Then quote only illegal characters (do not quote reserved,
        # unreserved, or '%')
        return quote(unquote_unreserved(uri), safe=safe_with_percent)
    except InvalidURL:
        # We couldn't unquote the given URI, so let's try quoting it, but
        # there may be unquoted '%'s in the URI. We need to make sure they're
        # properly quoted so they do not cause issues elsewhere.
        return quote(uri, safe=safe_without_percent)


def _get_mask_bits(mask: int, totalbits: int = 32) -> int:
    """Converts a mask from /xx format to an integer
    to be used as a mask for IP's in int format
    Example: if mask is 24 function returns 0xFFFFFF00
             if mask is 24 and totalbits=128 function
                returns 0xFFFFFF00000000000000000000000000
    """
    bits = ((1 << mask) - 1) << (totalbits - mask)

    return bits


def address_in_network(ip: str, net: str) -> bool:
    """This function allows you to check if an IP belongs to a network subnet

    Example: returns True if ip = 192.168.1.1 and net = 192.168.1.0/24
             returns False if ip = 192.168.1.1 and net = 192.168.100.0/24
             returns True if ip = 1:2:3:4::1 and net = 1:2:3:4::/64
    """
    netaddr, bits = net.split("/")
    if is_ipv4_address(ip) and is_ipv4_address(netaddr):
        ipaddr = struct.unpack(">L", socket.inet_aton(ip))[0]
        netmask = _get_mask_bits(int(bits))
        network = struct.unpack(">L", socket.inet_aton(netaddr))[0]
    elif is_ipv6_address(ip) and is_ipv6_address(netaddr):
        ipaddr_msb, ipaddr_lsb = struct.unpack(">QQ", socket.inet_pton(socket.AF_INET6, ip))
        ipaddr = (ipaddr_msb << 64) ^ ipaddr_lsb
        netmask = _get_mask_bits(int(bits), 128)
        network_msb, network_lsb = struct.unpack(">QQ", socket.inet_pton(socket.AF_INET6, netaddr))
        network = (network_msb << 64) ^ network_lsb
    else:
        return False
    return (ipaddr & netmask) == (network & netmask)


def dotted_netmask(mask: int) -> str:
    """Converts mask from /xx format to xxx.xxx.xxx.xxx

    Example: if mask is 24 function returns 255.255.255.0
    """
    bits = 0xFFFFFFFF ^ (1 << 32 - mask) - 1
    return socket.inet_ntoa(struct.pack(">I", bits))


def is_ipv4_address(string_ip: str) -> bool:
    try:
        socket.inet_aton(string_ip)
    except OSError:
        return False
    return True


def is_ipv6_address(string_ip: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET6, string_ip)
    except OSError:
        return False
    return True


def compare_ipv6(a: str, b: str):
    """
    Compare 2 IPs, uses socket.inet_pton to normalize IPv6 IPs
    """
    try:
        return socket.inet_pton(socket.AF_INET6, a) == socket.inet_pton(socket.AF_INET6, b)
    except OSError:
        return False


def is_valid_cidr(string_network: str) -> bool:
    """
    Very simple check of the cidr format in no_proxy variable.
    """
    if string_network.count("/") == 1:
        address, mask = string_network.split("/")

        if len(mask) >= 4 or mask.isdigit() is False:
            return False

        mask_int = int(mask)

        if is_ipv4_address(address):
            if mask_int < 1 or mask_int > 32:
                return False
        elif is_ipv6_address(address):
            if mask_int < 1 or mask_int > 128:
                return False
        else:
            return False
    else:
        return False
    return True


@contextlib.contextmanager
def set_environ(env_name: str, value: str | None) -> typing.Generator[None, None, None]:
    """Set the environment variable 'env_name' to 'value'

    Save previous value, yield, and then restore the previous value stored in
    the environment variable 'env_name'.

    If 'value' is None, do nothing"""
    value_changed = value is not None
    if value_changed:
        old_value = os.environ.get(env_name)
        os.environ[env_name] = value  # type: ignore[assignment]
    try:
        yield
    finally:
        if value_changed:
            if old_value is None:
                del os.environ[env_name]
            else:
                os.environ[env_name] = old_value


def should_bypass_proxies(url: str, no_proxy: str | None) -> bool:
    """
    Returns whether we should bypass proxies or not.
    """

    # Prioritize lowercase environment variables over uppercase
    # to keep a consistent behaviour with other http projects (curl, wget).
    def get_proxy(key: str) -> str | None:
        return os.environ.get(key) or os.environ.get(key.upper())

    # First check whether no_proxy is defined. If it is, check that the URL
    # we're getting isn't in the no_proxy list.
    no_proxy_arg = no_proxy
    if no_proxy is None:
        no_proxy = get_proxy("no_proxy")
    parsed = urlparse(url)

    if parsed.hostname is None:
        # URLs don't always have hostnames, e.g. file:/// urls.
        return True

    if no_proxy:
        # We need to check whether we match here. We need to see if we match
        # the end of the hostname, both with and without the port.
        no_proxy_list = list(host for host in no_proxy.replace(" ", "").split(",") if host)

        if is_ipv4_address(parsed.hostname) or is_ipv6_address(parsed.hostname):
            for proxy_ip in no_proxy_list:
                if is_valid_cidr(proxy_ip):
                    if address_in_network(parsed.hostname, proxy_ip):
                        return True
                elif parsed.hostname == proxy_ip:
                    # If no_proxy ip was defined in plain IP notation instead of cidr notation &
                    # matches the IP of the index
                    return True
                elif compare_ipv6(parsed.hostname, proxy_ip):
                    return True
        else:
            host_with_port = parsed.hostname
            if parsed.port:
                host_with_port += f":{parsed.port}"

            for host in no_proxy_list:
                if parsed.hostname.endswith(host) or host_with_port.endswith(host):
                    # The URL does match something in no_proxy, so we don't want
                    # to apply the proxies on this URL.
                    return True

    with set_environ("no_proxy", no_proxy_arg):
        # parsed.hostname can be `None` in cases such as a file URI.
        try:
            bypass = proxy_bypass(parsed.hostname)
        except (TypeError, socket.gaierror):
            bypass = False

    if bypass:
        return True

    return False


def get_environ_proxies(url: str, no_proxy: str | None = None) -> dict[str, str]:
    """
    Return a dict of environment proxies.
    """
    proxies = getproxies()

    if not proxies:
        return {}

    if should_bypass_proxies(url, no_proxy=no_proxy):
        return {}
    else:
        return proxies


def select_proxy(url: str, proxies: typing.Mapping[str, str | None] | None) -> str | None:
    """Select a proxy for the url, if applicable.

    :param url: The url being for the request
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    """
    proxies = proxies or {}

    if not proxies:
        return None

    urlparts = urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]

    if urlparts.scheme.lower() not in (
        "http",
        "https",
    ):
        maybe_extension_scheme = urlparts.scheme
        implementation = None

        if "+" in maybe_extension_scheme:
            maybe_extension_scheme, implementation = tuple(maybe_extension_scheme.split("+", maxsplit=1))

        try:
            extension_class = load_extension(maybe_extension_scheme, implementation)
        except ImportError:
            pass
        else:
            parent_scheme = extension_class.scheme_to_http_scheme(maybe_extension_scheme)

            proxy_keys.append(parent_scheme)
            proxy_keys.append(parent_scheme + "://" + urlparts.hostname)

    proxy = None
    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy


def resolve_proxies(
    request: PreparedRequest | Request,
    proxies: dict[str, str] | None,
    trust_env: bool = True,
) -> dict[str, str]:
    """This method takes proxy information from a request and configuration
    input to resolve a mapping of target proxies. This will consider settings
    such a NO_PROXY to strip proxy configurations.

    :param request: Request or PreparedRequest
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    :param trust_env: Boolean declaring whether to trust environment configs
    """
    proxies = proxies if proxies is not None else {}
    url = request.url

    assert url is not None, "PreparedRequest is not initialized correctly"

    scheme = parse_scheme(url)
    no_proxy = proxies.get("no_proxy")
    new_proxies = proxies.copy()

    if trust_env and not should_bypass_proxies(url, no_proxy=no_proxy):
        environ_proxies = get_environ_proxies(url, no_proxy=no_proxy)

        proxy = environ_proxies.get(scheme, environ_proxies.get("all"))

        if proxy:
            new_proxies.setdefault(scheme, proxy)
    return new_proxies


def default_user_agent(name: str = "niquests") -> str:
    """
    Return a string representing the default user agent.
    """
    return f"{name}/{__version__}"


def default_headers() -> CaseInsensitiveDict:
    return CaseInsensitiveDict(
        {
            "User-Agent": default_user_agent(),
            "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
    )


def parse_header_links(value: str) -> list[dict[str, str]]:
    """Return a list of parsed link headers proxies.

    i.e. Link: <http:/.../front.jpeg>; rel=front; type="image/jpeg",<http://.../back.jpeg>; rel=back;type="image/jpeg"
    """

    links: list[dict[str, str]] = []

    replace_chars = " '\""

    value = value.strip(replace_chars)
    if not value:
        return links

    for val in re.split(", *<", value):
        try:
            url, params = val.split(";", 1)
        except ValueError:
            url, params = val, ""

        link = {"url": url.strip("<> '\"")}

        for param in params.split(";"):
            try:
                key, value = param.split("=")
            except ValueError:
                break

            link[key.strip(replace_chars)] = value.strip(replace_chars)

        links.append(link)

    return links


def prepend_scheme_if_needed(url: str, new_scheme: str) -> str:
    """Given a URL that may or may not have a scheme, prepend the given scheme.
    Does not replace a present scheme with the one provided as an argument.
    """
    parsed = parse_url(url)
    scheme, auth, host, port, path, query, fragment = parsed

    # A defect in urlparse determines that there isn't a netloc present in some
    # urls. We previously assumed parsing was overly cautious, and swapped the
    # netloc and path. Due to a lack of tests on the original defect, this is
    # maintained with parse_url for backwards compatibility.
    netloc = parsed.netloc
    if not netloc:
        netloc, path = path, netloc

    if auth and netloc:
        # parse_url doesn't provide the netloc with auth
        # so we'll add it ourselves.
        netloc = "@".join([auth, netloc])
    if scheme is None:
        scheme = new_scheme
    if path is None:
        path = ""

    return urlunparse((scheme, netloc, path, "", query, fragment))


def get_auth_from_url(url: str) -> tuple[str, str]:
    """Given a url with authentication components, extract them into a tuple of
    username,password.
    """
    parsed = parse_url(url)

    if not parsed.auth or ":" not in parsed.auth:
        return "", ""

    username, password = tuple(parsed.auth.split(":", 1))

    try:
        auth = (unquote(username), unquote(password))  # type: ignore[arg-type]
    except (AttributeError, TypeError):
        auth = ("", "")

    return auth


def urldefragauth(url: str) -> str:
    """
    Given a url remove the fragment and the authentication part.
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)

    # see func:`prepend_scheme_if_needed`
    if not netloc:
        netloc, path = path, netloc

    netloc = netloc.rsplit("@", 1)[-1]

    return urlunparse((scheme, netloc, path, params, query, ""))


def rewind_body(prepared_request: PreparedRequest) -> None:
    """Move file pointer back to its recorded starting position
    so it can be read again on redirect.
    """
    body_seek = getattr(prepared_request.body, "seek", None)
    if body_seek is not None and isinstance(prepared_request._body_position, int):
        try:
            body_seek(prepared_request._body_position)
        except OSError:
            raise UnrewindableBodyError("An error occurred when rewinding request body for redirect.")
    else:
        raise UnrewindableBodyError("Unable to rewind request body for redirect.")


def create_resolver(definition: ResolverType | None) -> BaseResolver:
    """Instantiate a unique resolver, reusable across the Session scope."""
    if definition is None:
        overrule_dns = os.environ.get("NIQUESTS_DNS_URL", None)
        if overrule_dns is not None:
            definition = ResolverDescription.from_url(overrule_dns)
        else:
            return ResolverDescription(ProtocolResolver.SYSTEM).new()

    if isinstance(definition, BaseResolver):
        return definition

    if isinstance(definition, str):
        resolver = [ResolverDescription.from_url(definition)]
    elif isinstance(definition, ResolverDescription):
        resolver = [definition]
    elif isinstance(definition, list):
        if not definition:
            return ResolverDescription(ProtocolResolver.SYSTEM).new()
        if isinstance(definition[0], str):
            resolver = [ResolverDescription.from_url(e) for e in definition]  # type: ignore[arg-type]
        else:
            resolver = definition  # type: ignore[assignment]
    else:
        raise ValueError("invalid resolver definition given")

    resolvers: list[ResolverDescription] = []

    can_resolve_localhost: bool = False

    for resolver_description in resolver:
        if isinstance(resolver_description, str):
            resolvers.append(ResolverDescription.from_url(resolver_description))

            if resolvers[-1].protocol == ProtocolResolver.SYSTEM:
                can_resolve_localhost = True

            if "verify" in resolvers[-1] and resolvers[-1].kwargs["verify"] is False:
                resolvers[-1]["cert_reqs"] = 0
                del resolvers[-1].kwargs["verify"]

            continue

        resolvers.append(resolver_description)

        if "verify" in resolvers[-1] and resolvers[-1].kwargs["verify"] is False:
            resolvers[-1]["cert_reqs"] = 0
            del resolvers[-1].kwargs["verify"]

        if resolvers[-1].protocol == ProtocolResolver.SYSTEM:
            can_resolve_localhost = True

    if not can_resolve_localhost:
        resolvers.append(ResolverDescription.from_url("system://default?hosts=localhost"))

    #: We want to automatically forward ca_cert_data, ca_cert_dir, and ca_certs.
    for rd in resolvers:
        # If no CA bundle is provided, inject the system's default!
        if "ca_cert_data" not in rd and "ca_cert_dir" not in rd and "ca_certs" not in rd:
            rd["ca_cert_data"] = wassima.generate_ca_bundle()

    return ManyResolver(*[r.new() for r in resolvers])


def create_async_resolver(definition: AsyncResolverType | None) -> AsyncBaseResolver:
    """Instantiate a unique resolver, reusable across the Session scope."""
    if definition is None:
        overrule_dns = os.environ.get("NIQUESTS_DNS_URL", None)
        if overrule_dns is not None:
            definition = AsyncResolverDescription.from_url(overrule_dns)
        else:
            return AsyncResolverDescription(ProtocolResolver.SYSTEM).new()

    if isinstance(definition, AsyncBaseResolver):
        return definition

    if isinstance(definition, str):
        resolver = [AsyncResolverDescription.from_url(definition)]
    elif isinstance(definition, AsyncResolverDescription):
        resolver = [definition]
    elif isinstance(definition, list):  # can either be list of str or list of Resolver
        if not definition:
            return AsyncResolverDescription(ProtocolResolver.SYSTEM).new()
        if isinstance(definition[0], str):
            resolver = [AsyncResolverDescription.from_url(e) for e in definition]  # type: ignore[arg-type]
        else:
            resolver = definition  # type: ignore[assignment]
    else:
        raise ValueError("invalid resolver definition given")

    resolvers: list[AsyncResolverDescription] = []

    can_resolve_localhost: bool = False

    for resolver_description in resolver:
        if isinstance(resolver_description, str):
            resolvers.append(AsyncResolverDescription.from_url(resolver_description))

            if resolvers[-1].protocol == ProtocolResolver.SYSTEM:
                can_resolve_localhost = True

            if "verify" in resolvers[-1] and resolvers[-1].kwargs["verify"] is False:
                resolvers[-1]["cert_reqs"] = 0
                del resolvers[-1].kwargs["verify"]

            continue

        resolvers.append(resolver_description)

        if "verify" in resolvers[-1] and resolvers[-1].kwargs["verify"] is False:
            resolvers[-1]["cert_reqs"] = 0
            del resolvers[-1].kwargs["verify"]

        if resolvers[-1].protocol == ProtocolResolver.SYSTEM:
            can_resolve_localhost = True

    if not can_resolve_localhost:
        resolvers.append(AsyncResolverDescription.from_url("system://default?hosts=localhost"))

    #: We want to automatically forward ca_cert_data, ca_cert_dir, and ca_certs.
    for rd in resolvers:
        # If no CA bundle is provided, inject the system's default!
        if "ca_cert_data" not in rd and "ca_cert_dir" not in rd and "ca_certs" not in rd:
            rd["ca_cert_data"] = wassima.generate_ca_bundle()

    return AsyncManyResolver(*[r.new() for r in resolvers])


def resolve_socket_family(disable_ipv4: bool, disable_ipv6: bool) -> socket.AddressFamily:
    if disable_ipv4:
        return socket.AF_INET6
    if disable_ipv6:
        return socket.AF_INET
    return socket.AF_UNSPEC


def _swap_context(response: AsyncResponse | Response) -> None:
    response_class = response.__class__

    is_async = len(response_class.__bases__) == 1 and response_class.__bases__[0] is not object

    if is_async:
        response.__class__ = response_class.__bases__[0]
    else:
        response.__class__ = response_class.__subclasses__()[0]


def _deepcopy_ci(o: ConnectionInfo | None) -> ConnectionInfo | None:
    if o is None:
        return None

    n = ConnectionInfo()

    for attr, val in vars(o).items():
        setattr(n, attr, val)

    return n


def parse_scheme(url: str, default: str | None = None, max_length: int = 11) -> str:
    """We tend to extract url scheme often enough, but we were crazy
    enough to use urlparse for it...! We were wasting precious CPU cycles.
    Return used scheme url, lowercased."""
    try:
        scheme = url[: url.index(":", 1, max_length + 1)]
    except ValueError as e:
        if default is not None:
            return default
        raise MissingSchema(f"Invalid URL {url!r}: No scheme supplied. Perhaps you meant https://{url}?") from e

    return scheme.lower()


def is_ocsp_capable(conn_info: ConnectionInfo | None) -> bool:
    # we can't do anything in that case.
    if conn_info is None or conn_info.certificate_der is None or conn_info.certificate_dict is None:
        return False

    endpoints: list[str] = [  # type: ignore
        # exclude non-HTTP endpoint. like ldap.
        ep  # type: ignore
        for ep in list(conn_info.certificate_dict.get("OCSP", []))  # type: ignore
        if ep.startswith("http://")  # type: ignore
    ]

    # well... not all issued certificate have a OCSP entry. e.g. mkcert.
    if not endpoints:
        return False

    return True


def wrap_extension_for_http(
    extension: type[ExtensionFromHTTP],
) -> type[ExtensionFromHTTP]:
    """
    We want to properly map exceptions from bellow (urllib3-future) into our own exceptions.
    This function purposely wrap the extension class to achieve that.
    Warning: synchronous context only!
    """

    from .exceptions import (
        ChunkedEncodingError,
        ConnectionError,
        ContentDecodingError,
        InvalidHeader,
        ProxyError,
        ReadTimeout,
    )
    from .exceptions import (
        SSLError as RequestsSSLError,
    )
    from .packages.urllib3.exceptions import (
        ClosedPoolError,
        DecodeError,
        ProtocolError,
        ReadTimeoutError,
    )
    from .packages.urllib3.exceptions import (
        HTTPError as _HTTPError,
    )
    from .packages.urllib3.exceptions import (
        InvalidHeader as _InvalidHeader,
    )
    from .packages.urllib3.exceptions import (
        ProxyError as _ProxyError,
    )
    from .packages.urllib3.exceptions import (
        SSLError as _SSLError,
    )

    class _WrappedExtensionFromHTTP(extension):  # type: ignore[valid-type,misc]
        def next_payload(self, *args, **kwargs) -> str | bytes | None:
            try:
                return super().next_payload(*args, **kwargs)
            except ProtocolError as e:
                raise ChunkedEncodingError(e)
            except DecodeError as e:
                raise ContentDecodingError(e)
            except ReadTimeoutError as e:
                raise ReadTimeout(e)
            except _SSLError as e:
                raise RequestsSSLError(e)

        def send_payload(self, buf: str | bytes) -> None:
            try:
                super().send_payload(buf)
            except (ProtocolError, OSError) as err:
                raise ConnectionError(err)
            except ClosedPoolError as e:
                raise ConnectionError(e)
            except _ProxyError as e:
                raise ProxyError(e)
            except (_SSLError, _HTTPError) as e:
                if isinstance(e, _SSLError):
                    raise RequestsSSLError(e)
                elif isinstance(e, ReadTimeoutError):
                    raise ReadTimeout(e)
                elif isinstance(e, _InvalidHeader):
                    raise InvalidHeader(e)
                else:
                    raise

        def close(self) -> None:
            try:
                super().close()
            except (ProtocolError, OSError) as err:
                raise ConnectionError(err)
            except ClosedPoolError as e:
                raise ConnectionError(e)
            except _ProxyError as e:
                raise ProxyError(e)
            except (_SSLError, _HTTPError) as e:
                if isinstance(e, _SSLError):
                    raise RequestsSSLError(e)
                elif isinstance(e, ReadTimeoutError):
                    raise ReadTimeout(e)
                elif isinstance(e, _InvalidHeader):
                    raise InvalidHeader(e)
                else:
                    raise

    return _WrappedExtensionFromHTTP


def async_wrap_extension_for_http(
    extension: type[AsyncExtensionFromHTTP],
) -> type[AsyncExtensionFromHTTP]:
    """
    We want to properly map exceptions from bellow (urllib3-future) into our own exceptions.
    This function purposely wrap the extension class to achieve that.
    Warning: asynchronous context only!
    """

    from .exceptions import (
        ChunkedEncodingError,
        ConnectionError,
        ContentDecodingError,
        InvalidHeader,
        ProxyError,
        ReadTimeout,
    )
    from .exceptions import (
        SSLError as RequestsSSLError,
    )
    from .packages.urllib3.exceptions import (
        ClosedPoolError,
        DecodeError,
        ProtocolError,
        ReadTimeoutError,
    )
    from .packages.urllib3.exceptions import (
        HTTPError as _HTTPError,
    )
    from .packages.urllib3.exceptions import (
        InvalidHeader as _InvalidHeader,
    )
    from .packages.urllib3.exceptions import (
        ProxyError as _ProxyError,
    )
    from .packages.urllib3.exceptions import (
        SSLError as _SSLError,
    )

    class _AsyncWrappedExtensionFromHTTP(extension):  # type: ignore[valid-type,misc]
        async def next_payload(self, *args, **kwargs) -> str | bytes | None:
            try:
                return await super().next_payload(*args, **kwargs)
            except ProtocolError as e:
                raise ChunkedEncodingError(e)
            except DecodeError as e:
                raise ContentDecodingError(e)
            except ReadTimeoutError as e:
                raise ReadTimeout(e)
            except _SSLError as e:
                raise RequestsSSLError(e)

        async def send_payload(self, buf: str | bytes) -> None:
            try:
                await super().send_payload(buf)
            except (ProtocolError, OSError) as err:
                raise ConnectionError(err)
            except ClosedPoolError as e:
                raise ConnectionError(e)
            except _ProxyError as e:
                raise ProxyError(e)
            except (_SSLError, _HTTPError) as e:
                if isinstance(e, _SSLError):
                    raise RequestsSSLError(e)
                elif isinstance(e, ReadTimeoutError):
                    raise ReadTimeout(e)
                elif isinstance(e, _InvalidHeader):
                    raise InvalidHeader(e)
                else:
                    raise

        async def close(self) -> None:
            try:
                await super().close()
            except (ProtocolError, OSError) as err:
                raise ConnectionError(err)
            except ClosedPoolError as e:
                raise ConnectionError(e)
            except _ProxyError as e:
                raise ProxyError(e)
            except (_SSLError, _HTTPError) as e:
                if isinstance(e, _SSLError):
                    raise RequestsSSLError(e)
                elif isinstance(e, ReadTimeoutError):
                    raise ReadTimeout(e)
                elif isinstance(e, _InvalidHeader):
                    raise InvalidHeader(e)
                else:
                    raise

    return _AsyncWrappedExtensionFromHTTP

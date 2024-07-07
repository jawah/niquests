Release History
===============

3.7.1 (2024-07-07)
------------------

**Added**
- Official support for Python 3.13
  This has been tested outside GitHub CI due to httpbin unready state for 3.13[...]
- Support for asynchronous auth callables.
- Support for asynchronous bodies through `AsyncIterable` that yield either bytes or str.
- Support for purposely excluding a domain/port from connecting to QUIC/HTTP3 via the `quic_cache_layer` property of `Session`.
  In order to exclude `cloudflare.com` from HTTP3 auto-upgrade:
  ```python
  from niquests import Session

  s = Session()
  s.quic_cache_layer.exclude_domain("cloudflare.com")
  ```

**Fixed**
- auth argument not accepting a function according to static type checkers. (#133)
- RequestsCookieJar having a lock in `AsyncSession`. Its effect has been nullified to improve performances.

**Changed**
- urllib3-future lower bound version is raised to 2.8.902

3.7.0 (2024-06-24)
------------------

**Added**
- TransferProgress tracking in Response when downloading using `stream=True` based on the Content-Length. (#127)
  There's no easy way to track the "real" amount of bytes consumed using "iter_content" when the remote is
  sending a compressed body. This change makes it possible to track the amount of bytes consumed.
  The `Response` object now contain a property named `download_progress` that is either `None` or a `TransferProgress` object.
- HTTP/2 with prior knowledge over TLS or via an unencrypted connection.
  `disable_http1` toggle is now available through your `Session` constructor.
  In consequence, you may leverage all HTTP/2 capabilities like multiplexing using a plain (e.g. non-TLS) socket.
  You may enable/disable any protocols per Session object (but not all of them at once!).
  In non-TLS connections, you have to keep one of HTTP/1.1 or HTTP/2 enabled.
  Otherwise, one of HTTP/1.1, HTTP/2 or HTTP/3. A `RuntimeError` may be thrown if no protocol can be used in a
  given context.

**Changed**
- Relax main API constraint in get, head, options and delete methods / functions by accepting kwargs.
- urllib3-future lower bound version is raised to 2.8.900

3.6.7 (2024-06-19)
------------------

**Fixed**
- CaseInsensitiveDict repr (to string) causing an unexpected error when upstream have multiple values for a single header. (#129)

**Misc**
- Minor docs typos (#128)
- Reformated error messages in our OCSP module for better readability.
- Added real test cases for our OCSP module to ensure its reliability.

3.6.6 (2024-05-27)
------------------

**Fixed**
- ReasonFlag not properly translated to readable text when peer or intermediate certificate is revoked.

3.6.5 (2024-05-22)
------------------

**Fixed**
- Support `localhost` as a valid domain for cookies. The standard library does not allow this special
  domain. Researches showed that a valid domain should have at least two dots (e.g. abc.com. and xyz.tld. but not com.).
  Public suffixes cannot be used as a cookie domain for security reasons, but as `localhost` isn't one we are explicitly
  allowing it. Reported in https://github.com/httpie/cli/issues/602
  `RequestsCookieJar` set a default policy that circumvent that limitation, if you specified a custom cookie policy then this
  fix won't be applied.

**Changed**
- Lazy load the OCSP extension in order to improve the import performance.

**Removed**
- Class variable `disable_thread` in `AsyncSession` that is no longer relevant since the native asyncio implementation. (PR #122)

3.6.4 (2024-05-16)
------------------

**Changed**
- Avoid parsing X509 peer certificate in the certificate revocation check process over and over again.
- Avoid iterating over header items redundantly or needlessly.

3.6.3 (2024-05-06)
------------------

**Fixed**
- Fixed encoding data with None values and other objects. This was a regression introduced in our v3. #119

**Changed**
- Various minor performance improvements.

3.6.2 (2024-05-02)
------------------

**Fixed**
- "Help" program `python -m niquests.help` that depended on h2 while not required anymore.
- Minor performance regression in async while checking OCSP when certificate isn't eligible (e.g. no OCSP url provided).

**Changed**
- urllib3.future lower bound constraint has been raised to version 2.7.905 to ensure inclusion of jh2 instead of h2.

3.6.1 (2024-04-22)
------------------

**Fixed**
- Handling broken environments with a graceful exception with a detailed error message.

3.6.0 (2024-04-20)
------------------

**Added**
- Support for qh3 version 1.0.0
  This qh3 release enable a greater flexibility by dropping cryptography. We had to adapt the OCSP code as we
  relied on cryptography. HTTP/3 experience is greatly improved.

**Changed**
- urllib3.future lower bound constraint has been raised to version 2.7.904 to ensure support for the last qh3 release.

**Fixed**
- Improved compatibility with third party mocking tool that are bound to requests.
- OCSP check did not warn if the HTTP server responded with a non 2xx response in strict mode.

3.5.5 (2024-03-25)
------------------

**Added**
- Support for Happy Eyeballs. This feature is disabled by default, you must pass `happy_eyeballs=True` within your session
  constructor or http adapter in order to leverage this.

**Fixed**
- Missed close implementation in AsyncSession causing the underlying poolmanager to remain open.
- Additional OCSP requests (following a redirect) did not use specified custom DNS resolver.

**Changed**
- urllib3.future lower bound constraint has been raised to version 2.7.900 for the newly added happy eyeballs feature.

3.5.4 (2024-03-17)
------------------

**Added**
- Support to verify the peer certificate fingerprint using `verify=...` by passing a string using the following format:
  `verify="sha256_748c76348778cb4a536e7ec12bc9aa559c12770bd1419c7ffe516006e1dea0ec"`. Doing so disable the certificate
  usual verification and only checks for its fingerprint match.

**Fixed**
- Multiplexed request in async did not support awaitable in hooks.
- Setting `verify=...` and `cert=...` then change it for the same host did not apply to the underlying (existing) connection pool.

**Misc**
- Overall performance improvements in both async and sync requests.
- Update pre-commit dependencies (ruff, pyupgrade, and mypy).
- Fixed SessionRedirect in tests that produced an incomplete Response instance that wasn't suitable for tests.

3.5.3 (2024-03-06)
------------------

**Fixed**
- A rare error that occurs on PyPy, especially on Windows, complaining about a missing release call.

**Misc**
- Allow latest dependencies version for httpbin, Flask and werkzeug in tests.
- Remove wheel from test dependencies.

3.5.2 (2024-03-05)
------------------

**Fixed**
- ImportError in an attempt to retrieve `ConnectionInfo`.

**Changed**
- General performance improvements.

3.5.1 (2024-03-04)
------------------

**Changed**
- General performance improvements.

3.5.0 (2024-02-29)
------------------

**Changed**
- Replaced the thread pool executor for the true asyncio implementation. The asynchronous part is rewritten.
- urllib3.future lower bound constraint has been raised to version 2.6.900 for the newly added asynchronous interfaces.

**Added**
- Support for awaitable hooks in AsyncSession.
- Extendable AsyncBaseAdapter.
- Support for orjson if installed in environment to dramatically increase performance in JSON deserialization.
- Extra `speedups` to increase overall performances by including optional dependencies such as zstandard, brotli and orjson.

**Fixed**
- A rare error when leveraging multiplexing when a proxy is used.
- Bypass proxies when looking to validate certificate revocation status in Python < 3.10 with OCSP.

3.4.7 (2024-02-21)
------------------

**Fixed**
- Unintentional performance regression with multiple concurrent multiplexed connection within a single Session.

3.4.6 (2024-02-21)
------------------

**Fixed**
- Unmatched filter for deprecation warning yielded by Cryptography due to some legacy CA available in Windows having a negative serial number.
- Setting `boundary` in `Content-Type` header with no value associated (no equal sign) can cause a rare error (multipart).
- Rare racing condition while emitting too many request across a multiplexed connections.
- Spawning too many threads while using `AsyncSession` in specific contexts.

3.4.5 (2024-02-02)
------------------

**Fixed**
- Thread-safety issue when leveraging a single multiplexed connection across multiple threads.
- Apparently consumed content when allow_redirect is set to True when accessing a lazy response that follow redirects.

**Changed**
- urllib3.future lower bound constraint has been raised to version 2.5.900 in order to leverage the advanced multiplexing scheduler.
  This upgrade come with a noticeable performance bump.

**Added**
- ``Session`` constructor now accepts both ``pool_connections`` and ``pool_maxsize`` parameters to scale your pools of connections at will.

3.4.4 (2024-01-18)
------------------

**Fixed**
- Issuing a request with `Session(multiplexed=True)` that weren't eligible (e.g. HTTP/1.1) but was redirected to an
  eligible server (HTTP/2+) caused a rare error.
- An anonymous netrc entry (e.g. username only) could be wrongfully used when it should be discarded. (PR #61)

**Added**
- Awaitable close method within `AsyncSession`.

3.4.3 (2024-01-16)
------------------

**Fixed**
- Accessing a lazy response (multiplexed enabled) that have multiple redirects did not work appropriately.

**Changed**
- Response `iter_content` and `iter_line` read chunks as they arrive by default. The default chunk size is now `-1`.
  `-1` mean to instruct that the chunks can be of variable sizes, depending on how packets arrives. It improves
  overall performances.
- urllib3.future lower bound constraint has been raised to version 2.4.904 in order to accept `-1` as a chunk size.

3.4.2 (2024-01-11)
------------------

**Fixed**
- Connection information kept targeting its original copy, thus always keeping the latest timings inside while expecting the historical ones.

**Added**
- `AsyncSession` now returns a `AsyncResponse` when `stream` is set to True in order to handle properly streams in an async context.

3.4.1 (2024-01-07)
------------------

**Fixed**
- CaseInsensibleDict did not properly convert HTTPHeaderDict from urllib3 thus only letting the last entry in.
- Redirect chain lead to a non waited coroutine in `AsyncSession`.

3.4.0 (2024-01-01)
------------------

**Added**
- Support for specifying a custom DNS resolver in `Session`.
- Support for passing the source address in `Session`.
- Support for disabling either IPv4 or IPv6 within a `Session`.

**Changed**
- PySocks is no longer used for SOCKS proxies. Replaced by **python-socks** instead.
- urllib3.future minimal version raised to 2.4+ to leverage newly added features.
- Improve compatibility when end-user inadvertently pass a `Timeout` or `Retry` instance from the legacy `urllib3` instead of `urllib3_future`.

**Fixed**
- Blocking the event loop when closing the `AsyncSession` using `with`.
- Rare exception on older PyPy interpreters due to Generic having unsupported type variable in `extensions._sync_to_async` module.

**Misc**
- Project extras aligned with **urllib3.future**.
- Using nox instead of tox.
- Switch to ruff instead of black and isort.

3.3.4 (2023-12-03)
------------------

**Fixed**
- Overall static typing experience have been improved.
- Code HTTP 425 is now registered as `too_early` in addition to the legacy `unordered_collection`.

**Removed**
- Private module `niquests._internal_utils` has been removed as it no longer serve its purposes.

3.3.3 (2023-11-26)
------------------

**Added**
- Hook `on_upload` that allows you to monitor/track the upload progress.
- Model `TransferProgress` that is used in `PreparedRequest` as public property `upload_progress`.

3.3.2 (2023-11-19)
------------------

**Fixed**
- Hooks that does not accept keyword arguments are rejected.
- Applying `max_fetch` to `Session.gather(...)` did not prevent the adapter to drain all pending responses.
- Closed session having unconsumed multiplexed requests leaked an exception from urllib3.future.

**Changed**
- Aligned `qh3` version constraint in `http3` extra with urllib3.future.

3.3.1 (2023-11-18)
------------------

**Fixed**
- Warning filter (ignore) for `DependencyWarning` within urllib3.future wasn't applied in time.

3.3.0 (2023-11-18)
------------------

**Added**
- Maximum of (lazy) response(s) to be resolved when calling `Session.gather(..., max_fetch = ...)`.
  Specifying a valid int to `max_fetch` will stop right after having resolved the right amount of responses.

**Changed**
- urllib3.future minimal version raised to 2.3.900 to leverage the fallback top-level package `urllib3_future`.

**Fixed**
- Error when having accidentally overriden `urllib3.future` by an external dependency.
- Undesirable warning yielded by `cryptography` because of a Microsoft root certificate.
  "Parsed a negative serial number, which is disallowed by RFC 5280."
- Take into account newly registered custom CA when using `wassima.register_ca(...)`.

**Removed**
- Dependency check at runtime for `urllib3`. There's no more check and warnings at runtime for that subject. Ever.

3.2.4 (2023-11-15)
------------------

**Fixed**
- Compatibility with some third-party mock tools.

**Changed**
- Relax IllegalHeader constraint when value is an integer, or float.

3.2.3 (2023-11-11)
------------------

**Fixed**
- Overall performance improvement.
- Racing condition in `HTTPAdapter` with multiplexed enabled while in threads.

**Removed**
- Checks for header validity as it is duplicated (upstream does it already).
  Warning: Function `check_header_validity` has been removed. It was not public in the first place.

**Changed**
- Cached proxies from environment to avoid unnecessary scan on each request.

3.2.2 (2023-11-08)
------------------

**Changed**
- Enforced a maximum in-flight request when using multiplexed connections. Default to 124 per connections
  so, actually 1240 per Session (_default is 10 connections_). This can be overriden in our `HTTPAdapter` for advanced users.
  This limit was changed due to constraint in `qh3`, for now we have no way to dynamically set this. We choose the safest
  lowest common value in h2, and qh3.

**Fixed**
- Performance issues in `get_environ_proxies()`.


3.2.1 (2023-11-06)
------------------

**Fixed**
- Performance issues in HTTP/2, and HTTP/3, with or without multiplexed connections.

**Changed**
- Enforced a maximum in-flight request when using multiplexed connections. Default to 200 per connections
  so, actually 2000 per Session (_default is 10 connections_). This can be overriden in our `HTTPAdapter` for advanced users.

3.2.0 (2023-11-05)
------------------

**Changed**
- Changed method `raise_for_status` in class `Response` to return **self** in order to make the call chainable.
  Idea taken from upstream https://github.com/psf/requests/issues/6215
- Bump minimal version supported for `urllib3.future` to 2.2.901 for recently introduced added features (bellow).

**Added**
- Support for multiplexed connection in HTTP/2 and HTTP/3. Concurrent requests per connection are now a thing, in synchronous code.
  This feature is the real advantage of using binaries HTTP protocols.
  It is disabled by default and can be enabled through `Session(multiplexed=True)`, each `Response` object will
  be 'lazy' loaded. Accessing anything from returned `Response` will block the code until target response is retrieved.
  Use `Session.gather()` to efficiently receive responses. You may also give a list of responses that you want to load.

  **Example A)** Emitting concurrent requests and loading them via `Session.gather()`
  ```python
  from niquests import Session
  from time import time

  s = Session(multiplexed=True)

  before = time()
  responses = []

  responses.append(
    s.get("https://pie.dev/delay/3")
  )

  responses.append(
    s.get("https://pie.dev/delay/1")
  )

  s.gather()

  print(f"waited {time() - before} second(s)")  # will print 3s
  ```

  **Example B)** Emitting concurrent requests and loading them via direct access
  ```python
  from niquests import Session
  from time import time

  s = Session(multiplexed=True)

  before = time()
  responses = []

  responses.append(
    s.get("https://pie.dev/delay/3")
  )

  responses.append(
    s.get("https://pie.dev/delay/1")
  )

  # internally call gather with self (Response)
  print(responses[0].status_code)  # 200! :! Hidden call to s.gather(responses[0])
  print(responses[1].status_code)  # 200!

  print(f"waited {time() - before} second(s)")  # will print 3s
  ```
  You have nothing to do, everything from streams to connection pooling are handled automagically!
- Support for in-memory intermediary/client certificate (mTLS).
  Thanks for support within `urllib3.future`. Unfortunately this feature may not be available depending on your platform.
  Passing `cert=(a, b, c)` where **a** or/and **b** contains directly the certificate is supported.
  See https://urllib3future.readthedocs.io/en/latest/advanced-usage.html#in-memory-client-mtls-certificate for more information.
  It is proposed to circumvent recent pyOpenSSL complete removal.
- Detect if a new (stable) version is available when invoking `python -m niquests.help` and propose it for installation.
- Add the possibility to disable a specific protocol (e.g. HTTP/2, and/or HTTP/3) when constructing `Session`.
  Like so: `s = Session(disable_http2=..., disable_http3=...)` both options are set to `False`, thus letting them enabled.
  urllib3.future does not permit to disable HTTP/1.1 for now.
- Support passing a single `str` to `auth=...` in addition to actually supported types. It will be treated as a
  **Bearer** token, by default to the `Authorization` header. It's a shortcut. You may keep your own token prefix in given
  string (e.g. if not Bearer).
- Added `MultiplexingError` exception for anything related to failure with a multiplexed connection.
- Added **async** support through `AsyncSession` that utilize an underlying thread pool.
  ```python
  from niquests import AsyncSession
  import asyncio
  from time import time

  async def emit() -> None:
      responses = []

      async with AsyncSession(multiplexed=True) as s:
          responses.append(await s.get("https://pie.dev/get"))
          responses.append(await s.get("https://pie.dev/head"))

          await s.gather()

      print(responses)

  async def main() -> None:
      foo = asyncio.create_task(emit())
      bar = asyncio.create_task(emit())
      await foo
      await bar

  if __name__ == "__main__":
      before = time()
      asyncio.run(main())
      print(time() - before)
  ```
  Or without `multiplexing` if you want to keep multiple connections open per host per request.
  ```python
  from niquests import AsyncSession
  import asyncio
  from time import time

  async def emit() -> None:
      responses = []

      async with AsyncSession() as s:
          responses.append(await s.get("https://pie.dev/get"))
          responses.append(await s.get("https://pie.dev/head"))

      print(responses)

  async def main() -> None:
      foo = asyncio.create_task(emit())
      bar = asyncio.create_task(emit())
      await foo
      await bar

  if __name__ == "__main__":
      before = time()
      asyncio.run(main())
      print(time() - before)
  ```
  You may disable concurrent threads by setting `AsyncSession.no_thread = True`.

**Security**
- Certificate revocation verification may not be fired for subsequents requests in a specific condition (redirection).

3.1.4 (2023-10-23)
------------------

**Fixed**
- Static type checker not accepting **iterable\[str\]** for **data**. A fix in urllib3.future allows it since v2.1.902.
- Unattended override of manually provided **Authorization** if `.netrc` existed with an eligible entry.
  Taken from closed PR https://github.com/psf/requests/pull/6555 and initially raised in https://github.com/psf/requests/issues/3929

**Added**
- **oheaders** property in `Request`, and `PreparedRequest` in addition to `Response`.

3.1.3 (2023-10-19)
------------------

**Fixed**
- **oheaders** from a Response contains `Set-Cookie` entries when it should not.
- Static type checker not accepting **list\[str\]** in values for argument **param**.
- Static type checker not accepting **Iterable\[bytes\]** for **data**.
- Function proxy_bypass_registry for Windows may be fooled by insufficient control on our end.
  Patch taken from idle upstream PR https://github.com/psf/requests/pull/6302
- SSLError message related to the certificate revocation could print `None` instead of `unspecified` for the reason.

**Changed**
- Allow setting `None` in max_size for **SharableLimitedDict** to remove limits.
- Using `RLock` instead of `Lock` in **SharableLimitedDict**, and **InMemoryRevocationStatus** classes.

**Misc**
- Missing assert statements for test test_header_validation.
- Unrelated warnings are now silent in our test suite.
- Unexpected warning now trigger an error in our test suite.
- Removed `tests.compat`.
- Removed `test-readme`, `flake8`, and `publish` from Makefile.

**Added**
- Extra-dist install `http3` to force install HTTP/3 support in your environment if not present.
- Extra-dist install `ocsp` to force install certificate revocation support in your environment if not present.

3.1.2 (2023-10-16)
------------------

**Fixed**
- Static type checker not accepting **list\[str\]** in values for argument **data**.

**Misc**
- Changed the documentation theme by **furo**.

**Added**
- IPv6 support in the `NO_PROXY` environment variable or in the **proxies** (key no_proxy) argument.
  Patch taken from idle upstream PR https://github.com/psf/requests/pull/5953
- Preemptively register a website to be HTTP/3 capable prior to the first TLS over TCP handshake.
  You can do so by doing like:

  ```python
  from niquests import Session

  s = Session()
  s.quic_cache_layer.add_domain("cloudflare.com")
  ```
- Passed **data** will be converted to form-data if headers have a Content-Type header and is set to `multipart/form-data`.
  Otherwise, by default, it is still urlencoded. If you specified a boundary, it will be used, otherwise, a random one will
  be generated.

3.1.1 (2023-10-11)
------------------

**Fixed**
- Fixed `Transfer-Encoding` wrongfully added to headers when body is actually of length 0. Due to ambiguous return of `super_len` in niquests internals.
- Fixed accepting three-valued tuple for Timeout (connect, read, total) in addition of known (connect, read) tuple.

3.1.0 (2023-10-10)
------------------

**Misc**
- Static typing has been improved to provide a better development experience.

**Added**
- Certificate revocation verification via the OCSP protocol.

  This feature is broadly available and is enabled by default when `verify=True`.
  We decided to follow what browsers do by default, so Niquests follows by being non-strict.
  OCSP responses are expected to arrive in less than 200ms, otherwise ignored (e.g. OCSP is dropped).
  Niquests keeps in-memory the results until the size exceed 2,048 entries, then an algorithm choose an entry
  to be deleted (oldest request or the first one that ended in error).

  You can at your own discretion enable strict OCSP checks by passing the environment variable `NIQUESTS_STRICT_OCSP`
  with anything inside but `0`. In strict mode the maximum delay for response passes from 200ms to 1,000ms and
  raises an error or explicit warning.

  In non-strict mode, this security measure will be deactivated automatically if your usage is unreasonable.
  e.g. Making a hundred of requests to a hundred of domains, thus consuming resources that should have been
  allocated to browser users. This was made available for users with a limited target of domains to get
  a complementary security measure.

  Unless in strict-mode, the proxy configuration will be respected when given, as long as it specify
  a plain `http` proxy. This is meant for people who want privacy.

  This feature may not be available if the `cryptography` package is missing from your environment.
  Verify the availability after Niquests upgrade by running `python -m niquests.help`.

  There is several downside of using OCSP, Niquests knows it. It is not a silver bullet solution. But better than nothing.
  It does not apply to HTTPS proxies themselves. For now.

- Add property `ocsp_verified` in both `PreparedRequest`, and `Response` to have a clue on the post handshake verification.

  Will be `None` if no verification took place, `True` if the verification leads to a confirmation from the OCSP server
  that the certificate is valid, `False` otherwise.

**Changed**
- Bump lower version requirement for `urllib3.future` to 2.1.900 to ensure compatibility with newer features.
- Internal in-memory QUIC capabilities is now thread safe and limited to 12,288 entries.
- Pickling a `Session` object no-longer dump adapters or the QUIC in-memory capabilities, they are reset on setstate.

**Fixed**
- `conn_info` was unset if the response came after a redirect.

3.0.2 (2023-10-01)
------------------

**Changed**
- niquests.help show more information about direct dependencies.
- urllib3.future minimal version raised to 2.0.936 due to an important fixe on the QUIC layer.
- wassima minimal version raised to 1.0.1 in order to support certifi as fallback in rare case.

3.0.1 (2023-09-26)
------------------

**Fixed**
- Method `head` not accepting `allow_redirect` named argument.
- `PreparedRequest` did not uppercase the HTTP verb when constructed manually.

**Changed**
- Minor code refactor in the `text`, and `json` methods within the `Response` class to be more concise.

3.0.0 (2023-09-24)
------------------

**Added**
- Static type annotations thorough the whole package.
- `cert` argument for client authentication with certificate can now pass the password/passphrase using a 3-values tuple (cert, key, password).
  The three parameters in the tuple must be of type `str`.
- `verify` argument behavior has been extended and now accept your CA bundle as `str` instead of a path. It also accepts your CA bundle as `bytes` directly.
  This help when you do not have access to the fs.
- Operating system truststore will be used instead of `certifi`. Root CAs are automatically grabbed from your computer configuration.
- Oriented-object headers. Access them through the new property `oheaders` in your `Response`.
- Propagated the argument `retries` in `niquests.api` for all functions.
- Added argument `retries` in the `Session` constructor.
- Property `conn_info` to the `PreparedRequest` and `Response` that hold a reference to a `ConnectionInfo`.
  This class exposes the following properties: `certificate_der` _(bytes)_, `certificate_dict` _(dict)_ as provided by the standard
  library (ssl), `destination_address` _(tuple[ipAddress, portNumber])_, `cipher` _(str)_, `tls_version` _(TLSVersion)_, and `http_version`.
- Two hooks, namely `pre_send` and `pre_request`. The `pre_request` event is fired just after the initial construction of
  a `PreparedRequest` instance. Finally, the `pre_send` will be triggered just after picking a (live) connection
  for your request. The two events receive a `PreparedRequest` instance.

**Changed**
- Calling the method `json` from `Response` when no encoding was provided no longer relies on internal encoding inference.
  We fall back on `charset-normalizer` with a limited set of charsets allowed (UTF-8/16/32 or ASCII).
- No longer will the `text` method from `Response` return str if content cannot be decoded. It returns None instead.
- If specified charset in content-type does not exist (LookupError) the `text` method from `Response` will rely on charset detection.
- If specified charset in content-type is not made for text decoding (e.g. base64), the `text` method from `Response` returns None.
- With above four changes, the `json` method will raise `RequestsJSONDecodeError` when the payload (body) cannot be decoded.
- Passing invalid `files` description no longer _just skip_ invalid entries, it raises `ValueError` from now on.
- Non-str HTTP-Verb are refused.
- Passing `files` with minimal description (meaning no tuple but _just_ the fp) no longer guess its name when `fp.name` return bytes.
- No longer will the default timeout be unset, thus making you waiting indefinitely.
  Functions `get`, `head`, and `options` ships with a default of 30 seconds.
  Then `put`, `post`, `patch` and `delete` uses a default of 120 seconds.
  Finally, the `request` function also have 120 seconds.
- Basic authorization username and password are now encoded using utf-8 instead of latin-1 prior to being base64 encoded.


**Removed**
- Property `apparent_encoding` in favor of a discrete internal inference.
- Support for the legacy `chardet` detector in case it was present in environment.
  Extra `chardet_on_py3` is now unavailable.
- **requests.compat** no longer hold reference to _chardet_.
- Deprecated `requests.packages` that was meant to avoid breakage from people importing `urllib3` or `chardet` within this package.
  They were _vendored_ in early versions of Requests. A long time ago.
- Deprecated function `get_encodings_from_content` from utils.
- Deprecated function `get_unicode_from_response` from utils.
- BasicAuth middleware no-longer support anything else than `bytes` or `str` for username and password.
- `requests.compat` is stripped of every reference that no longer vary between supported interpreter version.
- Charset fall back **ISO-8859-1** when content-type is text and no charset was specified.
- Main function `get`, `post`, `put`, `patch`, `delete`, and `head` no longer accept **kwargs**. They have a fixed list of typed argument.
  It is no longer possible to specify non-supported additional keyword argument from a `Session` instance or directly through `requests.api` functions.
  e.g. function `delete` no-longer accept `json`, or `files` arguments. as per RFCs specifications. You can still override this behavior through the `request` function.
- Mixin classes `RequestEncodingMixin`, and `RequestHooksMixin` due to OOP violations. Now deported directly into child classes.
- Function `unicode_is_ascii` as it is part of the stable `str` stdlib on Python 3 or greater.
- Alias function `session` for `Session` context manager that was kept for BC reasons since the v1.
- pyOpenSSL/urllib3 injection in case built-in ssl module does not have SNI support as it is not the case anymore for every supported interpreters.
- Constant `DEFAULT_CA_BUNDLE_PATH`, and submodule `certs` due to dropping `certifi`.
- Function `extract_zipped_paths` because rendered useless as it was made to handle an edge case where `certifi` is "zipped".
- Extra `security` when installing this package. It was previously emptied in the previous major.
- Warning emitted when passing a file opened in text-mode instead of binary. urllib3.future can overrule
  the content-length if it detects an error. You should not encounter broken request being sent.
- Support for `simplejson` if was present in environment.
- Submodule `compat`.

**Fixed**
- An invalid content-type definition would cause the charset being evaluated to `True`, thus making the program crash.
- Given `proxies` could be mutated when environment proxies were evaluated and injected. This package should not modify your inputs.
  For context see https://github.com/psf/requests/issues/6118
- A server could specify a `Location` header that does not comply to HTTP specifications and could lead to an unexpected exception.
  We try to fall back to Unicode decoding if the typical and expected Latin-1 would fail. If that fails too, a proper exception is raised.
  For context see https://github.com/psf/requests/issues/6026
- Top-level init now specify correctly the exposed api. Fixes mypy error `.. does not explicitly export attribute ..`.

2.32.1 (2023-09-12)
-------------------

**Bugfixes**
- Fix QUIC cache when using requests.request without persistent Session

**Dependencies**
- urllib3.future minimal version supported raised to 2.0.932 (ship with critical fixes)

2.32.0 (2023-08-29)
-------------------

**Dependencies**
- ⚠️ Switch urllib3 for urllib3.future ⚠️
  This may contain minor breaking changes, so we advise careful testing and
  reviewing.

**Features**
- Support for HTTP/2.
- Support for HTTP/3 over QUIC.
- Added property `http_version` that return an integer (11, 20, and 30) within `Response` to identify which protocol has been negotiated.
- Added `quic_cache_layer` mutable mapping optional argument to `Session` for optional external caching of QUIC server capabilities.

**Improvements**
- HTTP/1.1 no longer relies on the standard library `http.client` but `h11`.
- Response representation `__repr__` now yield the HTTP version.

**Removed**
- Warning filter for `charset_normalizer` as it was removed long ago.

2.31.0 (2023-05-22)
-------------------

**Security**
- Versions of Requests between v2.3.0 and v2.30.0 are vulnerable to potential
  forwarding of `Proxy-Authorization` headers to destination servers when
  following HTTPS redirects.

  When proxies are defined with user info (https://user:pass@proxy:8080), Requests
  will construct a `Proxy-Authorization` header that is attached to the request to
  authenticate with the proxy.

  In cases where Requests receives a redirect response, it previously reattached
  the `Proxy-Authorization` header incorrectly, resulting in the value being
  sent through the tunneled connection to the destination server. Users who rely on
  defining their proxy credentials in the URL are *strongly* encouraged to upgrade
  to Requests 2.31.0+ to prevent unintentional leakage and rotate their proxy
  credentials once the change has been fully deployed.

  Users who do not use a proxy or do not supply their proxy credentials through
  the user information portion of their proxy URL are not subject to this
  vulnerability.

  Full details can be read in our [Github Security Advisory](https://github.com/psf/requests/security/advisories/GHSA-j8r2-6x86-q33q)
  and [CVE-2023-32681](https://nvd.nist.gov/vuln/detail/CVE-2023-32681).


2.30.0 (2023-05-03)
-------------------

**Dependencies**
- ⚠️ Added support for urllib3 2.0. ⚠️

  This may contain minor breaking changes so we advise careful testing and
  reviewing https://urllib3.readthedocs.io/en/latest/v2-migration-guide.html
  prior to upgrading.

  Users who wish to stay on urllib3 1.x can pin to `urllib3<2`.

2.29.0 (2023-04-26)
-------------------

**Improvements**

- Requests now defers chunked requests to the urllib3 implementation to improve
  standardization. (#6226)
- Requests relaxes header component requirements to support bytes/str subclasses. (#6356)

2.28.2 (2023-01-12)
-------------------

**Dependencies**

- Requests now supports charset\_normalizer 3.x. (#6261)

**Bugfixes**

- Updated MissingSchema exception to suggest https scheme rather than http. (#6188)

2.28.1 (2022-06-29)
-------------------

**Improvements**

- Speed optimization in `iter_content` with transition to `yield from`. (#6170)

**Dependencies**

- Added support for chardet 5.0.0 (#6179)
- Added support for charset-normalizer 2.1.0 (#6169)

2.28.0 (2022-06-09)
-------------------

**Deprecations**

- ⚠️ Requests has officially dropped support for Python 2.7. ⚠️ (#6091)
- Requests has officially dropped support for Python 3.6 (including pypy3.6). (#6091)

**Improvements**

- Wrap JSON parsing issues in Request's JSONDecodeError for payloads without
  an encoding to make `json()` API consistent. (#6097)
- Parse header components consistently, raising an InvalidHeader error in
  all invalid cases. (#6154)
- Added provisional 3.11 support with current beta build. (#6155)
- Requests got a makeover and we decided to paint it black. (#6095)

**Bugfixes**

- Fixed bug where setting `CURL_CA_BUNDLE` to an empty string would disable
  cert verification. All Requests 2.x versions before 2.28.0 are affected. (#6074)
- Fixed urllib3 exception leak, wrapping `urllib3.exceptions.SSLError` with
  `requests.exceptions.SSLError` for `content` and `iter_content`. (#6057)
- Fixed issue where invalid Windows registry entries caused proxy resolution
  to raise an exception rather than ignoring the entry. (#6149)
- Fixed issue where entire payload could be included in the error message for
  JSONDecodeError. (#6036)

2.27.1 (2022-01-05)
-------------------

**Bugfixes**

- Fixed parsing issue that resulted in the `auth` component being
  dropped from proxy URLs. (#6028)

2.27.0 (2022-01-03)
-------------------

**Improvements**

- Officially added support for Python 3.10. (#5928)

- Added a `requests.exceptions.JSONDecodeError` to unify JSON exceptions between
  Python 2 and 3. This gets raised in the `response.json()` method, and is
  backwards compatible as it inherits from previously thrown exceptions.
  Can be caught from `requests.exceptions.RequestException` as well. (#5856)

- Improved error text for misnamed `InvalidSchema` and `MissingSchema`
  exceptions. This is a temporary fix until exceptions can be renamed
  (Schema->Scheme). (#6017)

- Improved proxy parsing for proxy URLs missing a scheme. This will address
  recent changes to `urlparse` in Python 3.9+. (#5917)

**Bugfixes**

- Fixed defect in `extract_zipped_paths` which could result in an infinite loop
  for some paths. (#5851)

- Fixed handling for `AttributeError` when calculating length of files obtained
  by `Tarfile.extractfile()`. (#5239)

- Fixed urllib3 exception leak, wrapping `urllib3.exceptions.InvalidHeader` with
  `requests.exceptions.InvalidHeader`. (#5914)

- Fixed bug where two Host headers were sent for chunked requests. (#5391)

- Fixed regression in Requests 2.26.0 where `Proxy-Authorization` was
  incorrectly stripped from all requests sent with `Session.send`. (#5924)

- Fixed performance regression in 2.26.0 for hosts with a large number of
  proxies available in the environment. (#5924)

- Fixed idna exception leak, wrapping `UnicodeError` with
  `requests.exceptions.InvalidURL` for URLs with a leading dot (.) in the
  domain. (#5414)

**Deprecations**

- Requests support for Python 2.7 and 3.6 will be ending in 2022. While we
  don't have exact dates, Requests 2.27.x is likely to be the last release
  series providing support.

2.26.0 (2021-07-13)
-------------------

**Improvements**

- Requests now supports Brotli compression, if either the `brotli` or
  `brotlicffi` package is installed. (#5783)

- `Session.send` now correctly resolves proxy configurations from both
  the Session and Request. Behavior now matches `Session.request`. (#5681)

**Bugfixes**

- Fixed a race condition in zip extraction when using Requests in parallel
  from zip archive. (#5707)

**Dependencies**

- Instead of `chardet`, use the MIT-licensed `charset_normalizer` for Python3
  to remove license ambiguity for projects bundling requests. If `chardet`
  is already installed on your machine it will be used instead of `charset_normalizer`
  to keep backwards compatibility. (#5797)

  You can also install `chardet` while installing requests by
  specifying `[use_chardet_on_py3]` extra as follows:

    ```shell
    pip install "requests[use_chardet_on_py3]"
    ```

  Python2 still depends upon the `chardet` module.

- Requests now supports `idna` 3.x on Python 3. `idna` 2.x will continue to
  be used on Python 2 installations. (#5711)

**Deprecations**

- The `requests[security]` extra has been converted to a no-op install.
  PyOpenSSL is no longer the recommended secure option for Requests. (#5867)

- Requests has officially dropped support for Python 3.5. (#5867)

2.25.1 (2020-12-16)
-------------------

**Bugfixes**

- Requests now treats `application/json` as `utf8` by default. Resolving
  inconsistencies between `r.text` and `r.json` output. (#5673)

**Dependencies**

- Requests now supports chardet v4.x.

2.25.0 (2020-11-11)
-------------------

**Improvements**

- Added support for NETRC environment variable. (#5643)

**Dependencies**

- Requests now supports urllib3 v1.26.

**Deprecations**

- Requests v2.25.x will be the last release series with support for Python 3.5.
- The `requests[security]` extra is officially deprecated and will be removed
  in Requests v2.26.0.

2.24.0 (2020-06-17)
-------------------

**Improvements**

- pyOpenSSL TLS implementation is now only used if Python
  either doesn't have an `ssl` module or doesn't support
  SNI. Previously pyOpenSSL was unconditionally used if available.
  This applies even if pyOpenSSL is installed via the
  `requests[security]` extra (#5443)

- Redirect resolution should now only occur when
  `allow_redirects` is True. (#5492)

- No longer perform unnecessary Content-Length calculation for
  requests that won't use it. (#5496)

2.23.0 (2020-02-19)
-------------------

**Improvements**

- Remove defunct reference to `prefetch` in Session `__attrs__` (#5110)

**Bugfixes**

- Requests no longer outputs password in basic auth usage warning. (#5099)

**Dependencies**

- Pinning for `chardet` and `idna` now uses major version instead of minor.
  This hopefully reduces the need for releases every time a dependency is updated.

2.22.0 (2019-05-15)
-------------------

**Dependencies**

- Requests now supports urllib3 v1.25.2.
  (note: 1.25.0 and 1.25.1 are incompatible)

**Deprecations**

- Requests has officially stopped support for Python 3.4.

2.21.0 (2018-12-10)
-------------------

**Dependencies**

- Requests now supports idna v2.8.

2.20.1 (2018-11-08)
-------------------

**Bugfixes**

- Fixed bug with unintended Authorization header stripping for
  redirects using default ports (http/80, https/443).

2.20.0 (2018-10-18)
-------------------

**Bugfixes**

-   Content-Type header parsing is now case-insensitive (e.g.
    charset=utf8 v Charset=utf8).
-   Fixed exception leak where certain redirect urls would raise
    uncaught urllib3 exceptions.
-   Requests removes Authorization header from requests redirected
    from https to http on the same hostname. (CVE-2018-18074)
-   `should_bypass_proxies` now handles URIs without hostnames (e.g.
    files).

**Dependencies**

- Requests now supports urllib3 v1.24.

**Deprecations**

- Requests has officially stopped support for Python 2.6.

2.19.1 (2018-06-14)
-------------------

**Bugfixes**

-   Fixed issue where status\_codes.py's `init` function failed trying
    to append to a `__doc__` value of `None`.

2.19.0 (2018-06-12)
-------------------

**Improvements**

-   Warn user about possible slowdown when using cryptography version
    &lt; 1.3.4
-   Check for invalid host in proxy URL, before forwarding request to
    adapter.
-   Fragments are now properly maintained across redirects. (RFC7231
    7.1.2)
-   Removed use of cgi module to expedite library load time.
-   Added support for SHA-256 and SHA-512 digest auth algorithms.
-   Minor performance improvement to `Request.content`.
-   Migrate to using collections.abc for 3.7 compatibility.

**Bugfixes**

-   Parsing empty `Link` headers with `parse_header_links()` no longer
    return one bogus entry.
-   Fixed issue where loading the default certificate bundle from a zip
    archive would raise an `IOError`.
-   Fixed issue with unexpected `ImportError` on windows system which do
    not support `winreg` module.
-   DNS resolution in proxy bypass no longer includes the username and
    password in the request. This also fixes the issue of DNS queries
    failing on macOS.
-   Properly normalize adapter prefixes for url comparison.
-   Passing `None` as a file pointer to the `files` param no longer
    raises an exception.
-   Calling `copy` on a `RequestsCookieJar` will now preserve the cookie
    policy correctly.

**Dependencies**

-   We now support idna v2.7.
-   We now support urllib3 v1.23.

2.18.4 (2017-08-15)
-------------------

**Improvements**

-   Error messages for invalid headers now include the header name for
    easier debugging

**Dependencies**

-   We now support idna v2.6.

2.18.3 (2017-08-02)
-------------------

**Improvements**

-   Running `$ python -m requests.help` now includes the installed
    version of idna.

**Bugfixes**

-   Fixed issue where Requests would raise `ConnectionError` instead of
    `SSLError` when encountering SSL problems when using urllib3 v1.22.

2.18.2 (2017-07-25)
-------------------

**Bugfixes**

-   `requests.help` no longer fails on Python 2.6 due to the absence of
    `ssl.OPENSSL_VERSION_NUMBER`.

**Dependencies**

-   We now support urllib3 v1.22.

2.18.1 (2017-06-14)
-------------------

**Bugfixes**

-   Fix an error in the packaging whereby the `*.whl` contained
    incorrect data that regressed the fix in v2.17.3.

2.18.0 (2017-06-14)
-------------------

**Improvements**

-   `Response` is now a context manager, so can be used directly in a
    `with` statement without first having to be wrapped by
    `contextlib.closing()`.

**Bugfixes**

-   Resolve installation failure if multiprocessing is not available
-   Resolve tests crash if multiprocessing is not able to determine the
    number of CPU cores
-   Resolve error swallowing in utils set\_environ generator

2.17.3 (2017-05-29)
-------------------

**Improvements**

-   Improved `packages` namespace identity support, for monkeypatching
    libraries.

2.17.2 (2017-05-29)
-------------------

**Improvements**

-   Improved `packages` namespace identity support, for monkeypatching
    libraries.

2.17.1 (2017-05-29)
-------------------

**Improvements**

-   Improved `packages` namespace identity support, for monkeypatching
    libraries.

2.17.0 (2017-05-29)
-------------------

**Improvements**

-   Removal of the 301 redirect cache. This improves thread-safety.

2.16.5 (2017-05-28)
-------------------

-   Improvements to `$ python -m requests.help`.

2.16.4 (2017-05-27)
-------------------

-   Introduction of the `$ python -m requests.help` command, for
    debugging with maintainers!

2.16.3 (2017-05-27)
-------------------

-   Further restored the `requests.packages` namespace for compatibility
    reasons.

2.16.2 (2017-05-27)
-------------------

-   Further restored the `requests.packages` namespace for compatibility
    reasons.

No code modification (noted below) should be necessary any longer.

2.16.1 (2017-05-27)
-------------------

-   Restored the `requests.packages` namespace for compatibility
    reasons.
-   Bugfix for `urllib3` version parsing.

**Note**: code that was written to import against the
`requests.packages` namespace previously will have to import code that
rests at this module-level now.

For example:

    from requests.packages.urllib3.poolmanager import PoolManager

Will need to be re-written to be:

    from requests.packages import urllib3
    urllib3.poolmanager.PoolManager

Or, even better:

    from urllib3.poolmanager import PoolManager

2.16.0 (2017-05-26)
-------------------

-   Unvendor ALL the things!

2.15.1 (2017-05-26)
-------------------

-   Everyone makes mistakes.

2.15.0 (2017-05-26)
-------------------

**Improvements**

-   Introduction of the `Response.next` property, for getting the next
    `PreparedResponse` from a redirect chain (when
    `allow_redirects=False`).
-   Internal refactoring of `__version__` module.

**Bugfixes**

-   Restored once-optional parameter for
    `requests.utils.get_environ_proxies()`.

2.14.2 (2017-05-10)
-------------------

**Bugfixes**

-   Changed a less-than to an equal-to and an or in the dependency
    markers to widen compatibility with older setuptools releases.

2.14.1 (2017-05-09)
-------------------

**Bugfixes**

-   Changed the dependency markers to widen compatibility with older pip
    releases.

2.14.0 (2017-05-09)
-------------------

**Improvements**

-   It is now possible to pass `no_proxy` as a key to the `proxies`
    dictionary to provide handling similar to the `NO_PROXY` environment
    variable.
-   When users provide invalid paths to certificate bundle files or
    directories Requests now raises `IOError`, rather than failing at
    the time of the HTTPS request with a fairly inscrutable certificate
    validation error.
-   The behavior of `SessionRedirectMixin` was slightly altered.
    `resolve_redirects` will now detect a redirect by calling
    `get_redirect_target(response)` instead of directly querying
    `Response.is_redirect` and `Response.headers['location']`. Advanced
    users will be able to process malformed redirects more easily.
-   Changed the internal calculation of elapsed request time to have
    higher resolution on Windows.
-   Added `win_inet_pton` as conditional dependency for the `[socks]`
    extra on Windows with Python 2.7.
-   Changed the proxy bypass implementation on Windows: the proxy bypass
    check doesn't use forward and reverse DNS requests anymore
-   URLs with schemes that begin with `http` but are not `http` or
    `https` no longer have their host parts forced to lowercase.

**Bugfixes**

-   Much improved handling of non-ASCII `Location` header values in
    redirects. Fewer `UnicodeDecodeErrors` are encountered on Python 2,
    and Python 3 now correctly understands that Latin-1 is unlikely to
    be the correct encoding.
-   If an attempt to `seek` file to find out its length fails, we now
    appropriately handle that by aborting our content-length
    calculations.
-   Restricted `HTTPDigestAuth` to only respond to auth challenges made
    on 4XX responses, rather than to all auth challenges.
-   Fixed some code that was firing `DeprecationWarning` on Python 3.6.
-   The dismayed person emoticon (`/o\\`) no longer has a big head. I'm
    sure this is what you were all worrying about most.

**Miscellaneous**

-   Updated bundled urllib3 to v1.21.1.
-   Updated bundled chardet to v3.0.2.
-   Updated bundled idna to v2.5.
-   Updated bundled certifi to 2017.4.17.

2.13.0 (2017-01-24)
-------------------

**Features**

-   Only load the `idna` library when we've determined we need it. This
    will save some memory for users.

**Miscellaneous**

-   Updated bundled urllib3 to 1.20.
-   Updated bundled idna to 2.2.

2.12.5 (2017-01-18)
-------------------

**Bugfixes**

-   Fixed an issue with JSON encoding detection, specifically detecting
    big-endian UTF-32 with BOM.

2.12.4 (2016-12-14)
-------------------

**Bugfixes**

-   Fixed regression from 2.12.2 where non-string types were rejected in
    the basic auth parameters. While support for this behaviour has been
    re-added, the behaviour is deprecated and will be removed in the
    future.

2.12.3 (2016-12-01)
-------------------

**Bugfixes**

-   Fixed regression from v2.12.1 for URLs with schemes that begin with
    "http". These URLs have historically been processed as though they
    were HTTP-schemed URLs, and so have had parameters added. This was
    removed in v2.12.2 in an overzealous attempt to resolve problems
    with IDNA-encoding those URLs. This change was reverted: the other
    fixes for IDNA-encoding have been judged to be sufficient to return
    to the behaviour Requests had before v2.12.0.

2.12.2 (2016-11-30)
-------------------

**Bugfixes**

-   Fixed several issues with IDNA-encoding URLs that are technically
    invalid but which are widely accepted. Requests will now attempt to
    IDNA-encode a URL if it can but, if it fails, and the host contains
    only ASCII characters, it will be passed through optimistically.
    This will allow users to opt-in to using IDNA2003 themselves if they
    want to, and will also allow technically invalid but still common
    hostnames.
-   Fixed an issue where URLs with leading whitespace would raise
    `InvalidSchema` errors.
-   Fixed an issue where some URLs without the HTTP or HTTPS schemes
    would still have HTTP URL preparation applied to them.
-   Fixed an issue where Unicode strings could not be used in basic
    auth.
-   Fixed an issue encountered by some Requests plugins where
    constructing a Response object would cause `Response.content` to
    raise an `AttributeError`.

2.12.1 (2016-11-16)
-------------------

**Bugfixes**

-   Updated setuptools 'security' extra for the new PyOpenSSL backend in
    urllib3.

**Miscellaneous**

-   Updated bundled urllib3 to 1.19.1.

2.12.0 (2016-11-15)
-------------------

**Improvements**

-   Updated support for internationalized domain names from IDNA2003 to
    IDNA2008. This updated support is required for several forms of IDNs
    and is mandatory for .de domains.
-   Much improved heuristics for guessing content lengths: Requests will
    no longer read an entire `StringIO` into memory.
-   Much improved logic for recalculating `Content-Length` headers for
    `PreparedRequest` objects.
-   Improved tolerance for file-like objects that have no `tell` method
    but do have a `seek` method.
-   Anything that is a subclass of `Mapping` is now treated like a
    dictionary by the `data=` keyword argument.
-   Requests now tolerates empty passwords in proxy credentials, rather
    than stripping the credentials.
-   If a request is made with a file-like object as the body and that
    request is redirected with a 307 or 308 status code, Requests will
    now attempt to rewind the body object so it can be replayed.

**Bugfixes**

-   When calling `response.close`, the call to `close` will be
    propagated through to non-urllib3 backends.
-   Fixed issue where the `ALL_PROXY` environment variable would be
    preferred over scheme-specific variables like `HTTP_PROXY`.
-   Fixed issue where non-UTF8 reason phrases got severely mangled by
    falling back to decoding using ISO 8859-1 instead.
-   Fixed a bug where Requests would not correctly correlate cookies set
    when using custom Host headers if those Host headers did not use the
    native string type for the platform.

**Miscellaneous**

-   Updated bundled urllib3 to 1.19.
-   Updated bundled certifi certs to 2016.09.26.

2.11.1 (2016-08-17)
-------------------

**Bugfixes**

-   Fixed a bug when using `iter_content` with `decode_unicode=True` for
    streamed bodies would raise `AttributeError`. This bug was
    introduced in 2.11.
-   Strip Content-Type and Transfer-Encoding headers from the header
    block when following a redirect that transforms the verb from
    POST/PUT to GET.

2.11.0 (2016-08-08)
-------------------

**Improvements**

-   Added support for the `ALL_PROXY` environment variable.
-   Reject header values that contain leading whitespace or newline
    characters to reduce risk of header smuggling.

**Bugfixes**

-   Fixed occasional `TypeError` when attempting to decode a JSON
    response that occurred in an error case. Now correctly returns a
    `ValueError`.
-   Requests would incorrectly ignore a non-CIDR IP address in the
    `NO_PROXY` environment variables: Requests now treats it as a
    specific IP.
-   Fixed a bug when sending JSON data that could cause us to encounter
    obscure OpenSSL errors in certain network conditions (yes, really).
-   Added type checks to ensure that `iter_content` only accepts
    integers and `None` for chunk sizes.
-   Fixed issue where responses whose body had not been fully consumed
    would have the underlying connection closed but not returned to the
    connection pool, which could cause Requests to hang in situations
    where the `HTTPAdapter` had been configured to use a blocking
    connection pool.

**Miscellaneous**

-   Updated bundled urllib3 to 1.16.
-   Some previous releases accidentally accepted non-strings as
    acceptable header values. This release does not.

2.10.0 (2016-04-29)
-------------------

**New Features**

-   SOCKS Proxy Support! (requires PySocks;
    `$ pip install requests[socks]`)

**Miscellaneous**

-   Updated bundled urllib3 to 1.15.1.

2.9.2 (2016-04-29)
------------------

**Improvements**

-   Change built-in CaseInsensitiveDict (used for headers) to use
    OrderedDict as its underlying datastore.

**Bugfixes**

-   Don't use redirect\_cache if allow\_redirects=False
-   When passed objects that throw exceptions from `tell()`, send them
    via chunked transfer encoding instead of failing.
-   Raise a ProxyError for proxy related connection issues.

2.9.1 (2015-12-21)
------------------

**Bugfixes**

-   Resolve regression introduced in 2.9.0 that made it impossible to
    send binary strings as bodies in Python 3.
-   Fixed errors when calculating cookie expiration dates in certain
    locales.

**Miscellaneous**

-   Updated bundled urllib3 to 1.13.1.

2.9.0 (2015-12-15)
------------------

**Minor Improvements** (Backwards compatible)

-   The `verify` keyword argument now supports being passed a path to a
    directory of CA certificates, not just a single-file bundle.
-   Warnings are now emitted when sending files opened in text mode.
-   Added the 511 Network Authentication Required status code to the
    status code registry.

**Bugfixes**

-   For file-like objects that are not sought to the very beginning, we
    now send the content length for the number of bytes we will actually
    read, rather than the total size of the file, allowing partial file
    uploads.
-   When uploading file-like objects, if they are empty or have no
    obvious content length we set `Transfer-Encoding: chunked` rather
    than `Content-Length: 0`.
-   We correctly receive the response in buffered mode when uploading
    chunked bodies.
-   We now handle being passed a query string as a bytestring on Python
    3, by decoding it as UTF-8.
-   Sessions are now closed in all cases (exceptional and not) when
    using the functional API rather than leaking and waiting for the
    garbage collector to clean them up.
-   Correctly handle digest auth headers with a malformed `qop`
    directive that contains no token, by treating it the same as if no
    `qop` directive was provided at all.
-   Minor performance improvements when removing specific cookies by
    name.

**Miscellaneous**

-   Updated urllib3 to 1.13.

2.8.1 (2015-10-13)
------------------

**Bugfixes**

-   Update certificate bundle to match `certifi` 2015.9.6.2's weak
    certificate bundle.
-   Fix a bug in 2.8.0 where requests would raise `ConnectTimeout`
    instead of `ConnectionError`
-   When using the PreparedRequest flow, requests will now correctly
    respect the `json` parameter. Broken in 2.8.0.
-   When using the PreparedRequest flow, requests will now correctly
    handle a Unicode-string method name on Python 2. Broken in 2.8.0.

2.8.0 (2015-10-05)
------------------

**Minor Improvements** (Backwards Compatible)

-   Requests now supports per-host proxies. This allows the `proxies`
    dictionary to have entries of the form
    `{'<scheme>://<hostname>': '<proxy>'}`. Host-specific proxies will
    be used in preference to the previously-supported scheme-specific
    ones, but the previous syntax will continue to work.
-   `Response.raise_for_status` now prints the URL that failed as part
    of the exception message.
-   `requests.utils.get_netrc_auth` now takes an `raise_errors` kwarg,
    defaulting to `False`. When `True`, errors parsing `.netrc` files
    cause exceptions to be thrown.
-   Change to bundled projects import logic to make it easier to
    unbundle requests downstream.
-   Changed the default User-Agent string to avoid leaking data on
    Linux: now contains only the requests version.

**Bugfixes**

-   The `json` parameter to `post()` and friends will now only be used
    if neither `data` nor `files` are present, consistent with the
    documentation.
-   We now ignore empty fields in the `NO_PROXY` environment variable.
-   Fixed problem where `httplib.BadStatusLine` would get raised if
    combining `stream=True` with `contextlib.closing`.
-   Prevented bugs where we would attempt to return the same connection
    back to the connection pool twice when sending a Chunked body.
-   Miscellaneous minor internal changes.
-   Digest Auth support is now thread safe.

**Updates**

-   Updated urllib3 to 1.12.

2.7.0 (2015-05-03)
------------------

This is the first release that follows our new release process. For
more, see [our
documentation](https://requests.readthedocs.io/en/latest/community/release-process/).

**Bugfixes**

-   Updated urllib3 to 1.10.4, resolving several bugs involving chunked
    transfer encoding and response framing.

2.6.2 (2015-04-23)
------------------

**Bugfixes**

-   Fix regression where compressed data that was sent as chunked data
    was not properly decompressed. (\#2561)

2.6.1 (2015-04-22)
------------------

**Bugfixes**

-   Remove VendorAlias import machinery introduced in v2.5.2.
-   Simplify the PreparedRequest.prepare API: We no longer require the
    user to pass an empty list to the hooks keyword argument. (c.f.
    \#2552)
-   Resolve redirects now receives and forwards all of the original
    arguments to the adapter. (\#2503)
-   Handle UnicodeDecodeErrors when trying to deal with a unicode URL
    that cannot be encoded in ASCII. (\#2540)
-   Populate the parsed path of the URI field when performing Digest
    Authentication. (\#2426)
-   Copy a PreparedRequest's CookieJar more reliably when it is not an
    instance of RequestsCookieJar. (\#2527)

2.6.0 (2015-03-14)
------------------

**Bugfixes**

-   CVE-2015-2296: Fix handling of cookies on redirect. Previously a
    cookie without a host value set would use the hostname for the
    redirected URL exposing requests users to session fixation attacks
    and potentially cookie stealing. This was disclosed privately by
    Matthew Daley of [BugFuzz](https://bugfuzz.com). This affects all
    versions of requests from v2.1.0 to v2.5.3 (inclusive on both ends).
-   Fix error when requests is an `install_requires` dependency and
    `python setup.py test` is run. (\#2462)
-   Fix error when urllib3 is unbundled and requests continues to use
    the vendored import location.
-   Include fixes to `urllib3`'s header handling.
-   Requests' handling of unvendored dependencies is now more
    restrictive.

**Features and Improvements**

-   Support bytearrays when passed as parameters in the `files`
    argument. (\#2468)
-   Avoid data duplication when creating a request with `str`, `bytes`,
    or `bytearray` input to the `files` argument.

2.5.3 (2015-02-24)
------------------

**Bugfixes**

-   Revert changes to our vendored certificate bundle. For more context
    see (\#2455, \#2456, and <https://bugs.python.org/issue23476>)

2.5.2 (2015-02-23)
------------------

**Features and Improvements**

-   Add sha256 fingerprint support.
    ([shazow/urllib3\#540](https://github.com/shazow/urllib3/pull/540))
-   Improve the performance of headers.
    ([shazow/urllib3\#544](https://github.com/shazow/urllib3/pull/544))

**Bugfixes**

-   Copy pip's import machinery. When downstream redistributors remove
    requests.packages.urllib3 the import machinery will continue to let
    those same symbols work. Example usage in requests' documentation
    and 3rd-party libraries relying on the vendored copies of urllib3
    will work without having to fallback to the system urllib3.
-   Attempt to quote parts of the URL on redirect if unquoting and then
    quoting fails. (\#2356)
-   Fix filename type check for multipart form-data uploads. (\#2411)
-   Properly handle the case where a server issuing digest
    authentication challenges provides both auth and auth-int
    qop-values. (\#2408)
-   Fix a socket leak.
    ([shazow/urllib3\#549](https://github.com/shazow/urllib3/pull/549))
-   Fix multiple `Set-Cookie` headers properly.
    ([shazow/urllib3\#534](https://github.com/shazow/urllib3/pull/534))
-   Disable the built-in hostname verification.
    ([shazow/urllib3\#526](https://github.com/shazow/urllib3/pull/526))
-   Fix the behaviour of decoding an exhausted stream.
    ([shazow/urllib3\#535](https://github.com/shazow/urllib3/pull/535))

**Security**

-   Pulled in an updated `cacert.pem`.
-   Drop RC4 from the default cipher list.
    ([shazow/urllib3\#551](https://github.com/shazow/urllib3/pull/551))

2.5.1 (2014-12-23)
------------------

**Behavioural Changes**

-   Only catch HTTPErrors in raise\_for\_status (\#2382)

**Bugfixes**

-   Handle LocationParseError from urllib3 (\#2344)
-   Handle file-like object filenames that are not strings (\#2379)
-   Unbreak HTTPDigestAuth handler. Allow new nonces to be negotiated
    (\#2389)

2.5.0 (2014-12-01)
------------------

**Improvements**

-   Allow usage of urllib3's Retry object with HTTPAdapters (\#2216)
-   The `iter_lines` method on a response now accepts a delimiter with
    which to split the content (\#2295)

**Behavioural Changes**

-   Add deprecation warnings to functions in requests.utils that will be
    removed in 3.0 (\#2309)
-   Sessions used by the functional API are always closed (\#2326)
-   Restrict requests to HTTP/1.1 and HTTP/1.0 (stop accepting HTTP/0.9)
    (\#2323)

**Bugfixes**

-   Only parse the URL once (\#2353)
-   Allow Content-Length header to always be overridden (\#2332)
-   Properly handle files in HTTPDigestAuth (\#2333)
-   Cap redirect\_cache size to prevent memory abuse (\#2299)
-   Fix HTTPDigestAuth handling of redirects after authenticating
    successfully (\#2253)
-   Fix crash with custom method parameter to Session.request (\#2317)
-   Fix how Link headers are parsed using the regular expression library
    (\#2271)

**Documentation**

-   Add more references for interlinking (\#2348)
-   Update CSS for theme (\#2290)
-   Update width of buttons and sidebar (\#2289)
-   Replace references of Gittip with Gratipay (\#2282)
-   Add link to changelog in sidebar (\#2273)

2.4.3 (2014-10-06)
------------------

**Bugfixes**

-   Unicode URL improvements for Python 2.
-   Re-order JSON param for backwards compat.
-   Automatically defrag authentication schemes from host/pass URIs.
    ([\#2249](https://github.com/psf/requests/issues/2249))

2.4.2 (2014-10-05)
------------------

**Improvements**

-   FINALLY! Add json parameter for uploads!
    ([\#2258](https://github.com/psf/requests/pull/2258))
-   Support for bytestring URLs on Python 3.x
    ([\#2238](https://github.com/psf/requests/pull/2238))

**Bugfixes**

-   Avoid getting stuck in a loop
    ([\#2244](https://github.com/psf/requests/pull/2244))
-   Multiple calls to iter\* fail with unhelpful error.
    ([\#2240](https://github.com/psf/requests/issues/2240),
    [\#2241](https://github.com/psf/requests/issues/2241))

**Documentation**

-   Correct redirection introduction
    ([\#2245](https://github.com/psf/requests/pull/2245/))
-   Added example of how to send multiple files in one request.
    ([\#2227](https://github.com/psf/requests/pull/2227/))
-   Clarify how to pass a custom set of CAs
    ([\#2248](https://github.com/psf/requests/pull/2248/))

2.4.1 (2014-09-09)
------------------

-   Now has a "security" package extras set,
    `$ pip install requests[security]`
-   Requests will now use Certifi if it is available.
-   Capture and re-raise urllib3 ProtocolError
-   Bugfix for responses that attempt to redirect to themselves forever
    (wtf?).

2.4.0 (2014-08-29)
------------------

**Behavioral Changes**

-   `Connection: keep-alive` header is now sent automatically.

**Improvements**

-   Support for connect timeouts! Timeout now accepts a tuple (connect,
    read) which is used to set individual connect and read timeouts.
-   Allow copying of PreparedRequests without headers/cookies.
-   Updated bundled urllib3 version.
-   Refactored settings loading from environment -- new
    Session.merge\_environment\_settings.
-   Handle socket errors in iter\_content.

2.3.0 (2014-05-16)
------------------

**API Changes**

-   New `Response` property `is_redirect`, which is true when the
    library could have processed this response as a redirection (whether
    or not it actually did).
-   The `timeout` parameter now affects requests with both `stream=True`
    and `stream=False` equally.
-   The change in v2.0.0 to mandate explicit proxy schemes has been
    reverted. Proxy schemes now default to `http://`.
-   The `CaseInsensitiveDict` used for HTTP headers now behaves like a
    normal dictionary when references as string or viewed in the
    interpreter.

**Bugfixes**

-   No longer expose Authorization or Proxy-Authorization headers on
    redirect. Fix CVE-2014-1829 and CVE-2014-1830 respectively.
-   Authorization is re-evaluated each redirect.
-   On redirect, pass url as native strings.
-   Fall-back to autodetected encoding for JSON when Unicode detection
    fails.
-   Headers set to `None` on the `Session` are now correctly not sent.
-   Correctly honor `decode_unicode` even if it wasn't used earlier in
    the same response.
-   Stop advertising `compress` as a supported Content-Encoding.
-   The `Response.history` parameter is now always a list.
-   Many, many `urllib3` bugfixes.

2.2.1 (2014-01-23)
------------------

**Bugfixes**

-   Fixes incorrect parsing of proxy credentials that contain a literal
    or encoded '\#' character.
-   Assorted urllib3 fixes.

2.2.0 (2014-01-09)
------------------

**API Changes**

-   New exception: `ContentDecodingError`. Raised instead of `urllib3`
    `DecodeError` exceptions.

**Bugfixes**

-   Avoid many many exceptions from the buggy implementation of
    `proxy_bypass` on OS X in Python 2.6.
-   Avoid crashing when attempting to get authentication credentials
    from \~/.netrc when running as a user without a home directory.
-   Use the correct pool size for pools of connections to proxies.
-   Fix iteration of `CookieJar` objects.
-   Ensure that cookies are persisted over redirect.
-   Switch back to using chardet, since it has merged with charade.

2.1.0 (2013-12-05)
------------------

-   Updated CA Bundle, of course.
-   Cookies set on individual Requests through a `Session` (e.g. via
    `Session.get()`) are no longer persisted to the `Session`.
-   Clean up connections when we hit problems during chunked upload,
    rather than leaking them.
-   Return connections to the pool when a chunked upload is successful,
    rather than leaking it.
-   Match the HTTPbis recommendation for HTTP 301 redirects.
-   Prevent hanging when using streaming uploads and Digest Auth when a
    401 is received.
-   Values of headers set by Requests are now always the native string
    type.
-   Fix previously broken SNI support.
-   Fix accessing HTTP proxies using proxy authentication.
-   Unencode HTTP Basic usernames and passwords extracted from URLs.
-   Support for IP address ranges for no\_proxy environment variable
-   Parse headers correctly when users override the default `Host:`
    header.
-   Avoid munging the URL in case of case-sensitive servers.
-   Looser URL handling for non-HTTP/HTTPS urls.
-   Accept unicode methods in Python 2.6 and 2.7.
-   More resilient cookie handling.
-   Make `Response` objects pickleable.
-   Actually added MD5-sess to Digest Auth instead of pretending to like
    last time.
-   Updated internal urllib3.
-   Fixed @Lukasa's lack of taste.

2.0.1 (2013-10-24)
------------------

-   Updated included CA Bundle with new mistrusts and automated process
    for the future
-   Added MD5-sess to Digest Auth
-   Accept per-file headers in multipart file POST messages.
-   Fixed: Don't send the full URL on CONNECT messages.
-   Fixed: Correctly lowercase a redirect scheme.
-   Fixed: Cookies not persisted when set via functional API.
-   Fixed: Translate urllib3 ProxyError into a requests ProxyError
    derived from ConnectionError.
-   Updated internal urllib3 and chardet.

2.0.0 (2013-09-24)
------------------

**API Changes:**

-   Keys in the Headers dictionary are now native strings on all Python
    versions, i.e. bytestrings on Python 2, unicode on Python 3.
-   Proxy URLs now *must* have an explicit scheme. A `MissingSchema`
    exception will be raised if they don't.
-   Timeouts now apply to read time if `Stream=False`.
-   `RequestException` is now a subclass of `IOError`, not
    `RuntimeError`.
-   Added new method to `PreparedRequest` objects:
    `PreparedRequest.copy()`.
-   Added new method to `Session` objects: `Session.update_request()`.
    This method updates a `Request` object with the data (e.g. cookies)
    stored on the `Session`.
-   Added new method to `Session` objects: `Session.prepare_request()`.
    This method updates and prepares a `Request` object, and returns the
    corresponding `PreparedRequest` object.
-   Added new method to `HTTPAdapter` objects:
    `HTTPAdapter.proxy_headers()`. This should not be called directly,
    but improves the subclass interface.
-   `httplib.IncompleteRead` exceptions caused by incorrect chunked
    encoding will now raise a Requests `ChunkedEncodingError` instead.
-   Invalid percent-escape sequences now cause a Requests `InvalidURL`
    exception to be raised.
-   HTTP 208 no longer uses reason phrase `"im_used"`. Correctly uses
    `"already_reported"`.
-   HTTP 226 reason added (`"im_used"`).

**Bugfixes:**

-   Vastly improved proxy support, including the CONNECT verb. Special
    thanks to the many contributors who worked towards this improvement.
-   Cookies are now properly managed when 401 authentication responses
    are received.
-   Chunked encoding fixes.
-   Support for mixed case schemes.
-   Better handling of streaming downloads.
-   Retrieve environment proxies from more locations.
-   Minor cookies fixes.
-   Improved redirect behaviour.
-   Improved streaming behaviour, particularly for compressed data.
-   Miscellaneous small Python 3 text encoding bugs.
-   `.netrc` no longer overrides explicit auth.
-   Cookies set by hooks are now correctly persisted on Sessions.
-   Fix problem with cookies that specify port numbers in their host
    field.
-   `BytesIO` can be used to perform streaming uploads.
-   More generous parsing of the `no_proxy` environment variable.
-   Non-string objects can be passed in data values alongside files.

1.2.3 (2013-05-25)
------------------

-   Simple packaging fix

1.2.2 (2013-05-23)
------------------

-   Simple packaging fix

1.2.1 (2013-05-20)
------------------

-   301 and 302 redirects now change the verb to GET for all verbs, not
    just POST, improving browser compatibility.
-   Python 3.3.2 compatibility
-   Always percent-encode location headers
-   Fix connection adapter matching to be most-specific first
-   new argument to the default connection adapter for passing a block
    argument
-   prevent a KeyError when there's no link headers

1.2.0 (2013-03-31)
------------------

-   Fixed cookies on sessions and on requests
-   Significantly change how hooks are dispatched - hooks now receive
    all the arguments specified by the user when making a request so
    hooks can make a secondary request with the same parameters. This is
    especially necessary for authentication handler authors
-   certifi support was removed
-   Fixed bug where using OAuth 1 with body `signature_type` sent no
    data
-   Major proxy work thanks to @Lukasa including parsing of proxy
    authentication from the proxy url
-   Fix DigestAuth handling too many 401s
-   Update vendored urllib3 to include SSL bug fixes
-   Allow keyword arguments to be passed to `json.loads()` via the
    `Response.json()` method
-   Don't send `Content-Length` header by default on `GET` or `HEAD`
    requests
-   Add `elapsed` attribute to `Response` objects to time how long a
    request took.
-   Fix `RequestsCookieJar`
-   Sessions and Adapters are now picklable, i.e., can be used with the
    multiprocessing library
-   Update charade to version 1.0.3

The change in how hooks are dispatched will likely cause a great deal of
issues.

1.1.0 (2013-01-10)
------------------

-   CHUNKED REQUESTS
-   Support for iterable response bodies
-   Assume servers persist redirect params
-   Allow explicit content types to be specified for file data
-   Make merge\_kwargs case-insensitive when looking up keys

1.0.3 (2012-12-18)
------------------

-   Fix file upload encoding bug
-   Fix cookie behavior

1.0.2 (2012-12-17)
------------------

-   Proxy fix for HTTPAdapter.

1.0.1 (2012-12-17)
------------------

-   Cert verification exception bug.
-   Proxy fix for HTTPAdapter.

1.0.0 (2012-12-17)
------------------

-   Massive Refactor and Simplification
-   Switch to Apache 2.0 license
-   Swappable Connection Adapters
-   Mountable Connection Adapters
-   Mutable ProcessedRequest chain
-   /s/prefetch/stream
-   Removal of all configuration
-   Standard library logging
-   Make Response.json() callable, not property.
-   Usage of new charade project, which provides python 2 and 3
    simultaneous chardet.
-   Removal of all hooks except 'response'
-   Removal of all authentication helpers (OAuth, Kerberos)

This is not a backwards compatible change.

0.14.2 (2012-10-27)
-------------------

-   Improved mime-compatible JSON handling
-   Proxy fixes
-   Path hack fixes
-   Case-Insensitive Content-Encoding headers
-   Support for CJK parameters in form posts

0.14.1 (2012-10-01)
-------------------

-   Python 3.3 Compatibility
-   Simply default accept-encoding
-   Bugfixes

0.14.0 (2012-09-02)
-------------------

-   No more iter\_content errors if already downloaded.

0.13.9 (2012-08-25)
-------------------

-   Fix for OAuth + POSTs
-   Remove exception eating from dispatch\_hook
-   General bugfixes

0.13.8 (2012-08-21)
-------------------

-   Incredible Link header support :)

0.13.7 (2012-08-19)
-------------------

-   Support for (key, value) lists everywhere.
-   Digest Authentication improvements.
-   Ensure proxy exclusions work properly.
-   Clearer UnicodeError exceptions.
-   Automatic casting of URLs to strings (fURL and such)
-   Bugfixes.

0.13.6 (2012-08-06)
-------------------

-   Long awaited fix for hanging connections!

0.13.5 (2012-07-27)
-------------------

-   Packaging fix

0.13.4 (2012-07-27)
-------------------

-   GSSAPI/Kerberos authentication!
-   App Engine 2.7 Fixes!
-   Fix leaking connections (from urllib3 update)
-   OAuthlib path hack fix
-   OAuthlib URL parameters fix.

0.13.3 (2012-07-12)
-------------------

-   Use simplejson if available.
-   Do not hide SSLErrors behind Timeouts.
-   Fixed param handling with urls containing fragments.
-   Significantly improved information in User Agent.
-   client certificates are ignored when verify=False

0.13.2 (2012-06-28)
-------------------

-   Zero dependencies (once again)!
-   New: Response.reason
-   Sign querystring parameters in OAuth 1.0
-   Client certificates no longer ignored when verify=False
-   Add openSUSE certificate support

0.13.1 (2012-06-07)
-------------------

-   Allow passing a file or file-like object as data.
-   Allow hooks to return responses that indicate errors.
-   Fix Response.text and Response.json for body-less responses.

0.13.0 (2012-05-29)
-------------------

-   Removal of Requests.async in favor of
    [grequests](https://github.com/kennethreitz/grequests)
-   Allow disabling of cookie persistence.
-   New implementation of safe\_mode
-   cookies.get now supports default argument
-   Session cookies not saved when Session.request is called with
    return\_response=False
-   Env: no\_proxy support.
-   RequestsCookieJar improvements.
-   Various bug fixes.

0.12.1 (2012-05-08)
-------------------

-   New `Response.json` property.
-   Ability to add string file uploads.
-   Fix out-of-range issue with iter\_lines.
-   Fix iter\_content default size.
-   Fix POST redirects containing files.

0.12.0 (2012-05-02)
-------------------

-   EXPERIMENTAL OAUTH SUPPORT!
-   Proper CookieJar-backed cookies interface with awesome dict-like
    interface.
-   Speed fix for non-iterated content chunks.
-   Move `pre_request` to a more usable place.
-   New `pre_send` hook.
-   Lazily encode data, params, files.
-   Load system Certificate Bundle if `certify` isn't available.
-   Cleanups, fixes.

0.11.2 (2012-04-22)
-------------------

-   Attempt to use the OS's certificate bundle if `certifi` isn't
    available.
-   Infinite digest auth redirect fix.
-   Multi-part file upload improvements.
-   Fix decoding of invalid %encodings in URLs.
-   If there is no content in a response don't throw an error the second
    time that content is attempted to be read.
-   Upload data on redirects.

0.11.1 (2012-03-30)
-------------------

-   POST redirects now break RFC to do what browsers do: Follow up with
    a GET.
-   New `strict_mode` configuration to disable new redirect behavior.

0.11.0 (2012-03-14)
-------------------

-   Private SSL Certificate support
-   Remove select.poll from Gevent monkeypatching
-   Remove redundant generator for chunked transfer encoding
-   Fix: Response.ok raises Timeout Exception in safe\_mode

0.10.8 (2012-03-09)
-------------------

-   Generate chunked ValueError fix
-   Proxy configuration by environment variables
-   Simplification of iter\_lines.
-   New trust\_env configuration for disabling system/environment hints.
-   Suppress cookie errors.

0.10.7 (2012-03-07)
-------------------

-   encode\_uri = False

0.10.6 (2012-02-25)
-------------------

-   Allow '=' in cookies.

0.10.5 (2012-02-25)
-------------------

-   Response body with 0 content-length fix.
-   New async.imap.
-   Don't fail on netrc.

0.10.4 (2012-02-20)
-------------------

-   Honor netrc.

0.10.3 (2012-02-20)
-------------------

-   HEAD requests don't follow redirects anymore.
-   raise\_for\_status() doesn't raise for 3xx anymore.
-   Make Session objects picklable.
-   ValueError for invalid schema URLs.

0.10.2 (2012-01-15)
-------------------

-   Vastly improved URL quoting.
-   Additional allowed cookie key values.
-   Attempted fix for "Too many open files" Error
-   Replace unicode errors on first pass, no need for second pass.
-   Append '/' to bare-domain urls before query insertion.
-   Exceptions now inherit from RuntimeError.
-   Binary uploads + auth fix.
-   Bugfixes.

0.10.1 (2012-01-23)
-------------------

-   PYTHON 3 SUPPORT!
-   Dropped 2.5 Support. (*Backwards Incompatible*)

0.10.0 (2012-01-21)
-------------------

-   `Response.content` is now bytes-only. (*Backwards Incompatible*)
-   New `Response.text` is unicode-only.
-   If no `Response.encoding` is specified and `chardet` is available,
    `Response.text` will guess an encoding.
-   Default to ISO-8859-1 (Western) encoding for "text" subtypes.
-   Removal of decode\_unicode. (*Backwards Incompatible*)
-   New multiple-hooks system.
-   New `Response.register_hook` for registering hooks within the
    pipeline.
-   `Response.url` is now Unicode.

0.9.3 (2012-01-18)
------------------

-   SSL verify=False bugfix (apparent on windows machines).

0.9.2 (2012-01-18)
------------------

-   Asynchronous async.send method.
-   Support for proper chunk streams with boundaries.
-   session argument for Session classes.
-   Print entire hook tracebacks, not just exception instance.
-   Fix response.iter\_lines from pending next line.
-   Fix but in HTTP-digest auth w/ URI having query strings.
-   Fix in Event Hooks section.
-   Urllib3 update.

0.9.1 (2012-01-06)
------------------

-   danger\_mode for automatic Response.raise\_for\_status()
-   Response.iter\_lines refactor

0.9.0 (2011-12-28)
------------------

-   verify ssl is default.

0.8.9 (2011-12-28)
------------------

-   Packaging fix.

0.8.8 (2011-12-28)
------------------

-   SSL CERT VERIFICATION!
-   Release of Cerifi: Mozilla's cert list.
-   New 'verify' argument for SSL requests.
-   Urllib3 update.

0.8.7 (2011-12-24)
------------------

-   iter\_lines last-line truncation fix
-   Force safe\_mode for async requests
-   Handle safe\_mode exceptions more consistently
-   Fix iteration on null responses in safe\_mode

0.8.6 (2011-12-18)
------------------

-   Socket timeout fixes.
-   Proxy Authorization support.

0.8.5 (2011-12-14)
------------------

-   Response.iter\_lines!

0.8.4 (2011-12-11)
------------------

-   Prefetch bugfix.
-   Added license to installed version.

0.8.3 (2011-11-27)
------------------

-   Converted auth system to use simpler callable objects.
-   New session parameter to API methods.
-   Display full URL while logging.

0.8.2 (2011-11-19)
------------------

-   New Unicode decoding system, based on over-ridable
    Response.encoding.
-   Proper URL slash-quote handling.
-   Cookies with `[`, `]`, and `_` allowed.

0.8.1 (2011-11-15)
------------------

-   URL Request path fix
-   Proxy fix.
-   Timeouts fix.

0.8.0 (2011-11-13)
------------------

-   Keep-alive support!
-   Complete removal of Urllib2
-   Complete removal of Poster
-   Complete removal of CookieJars
-   New ConnectionError raising
-   Safe\_mode for error catching
-   prefetch parameter for request methods
-   OPTION method
-   Async pool size throttling
-   File uploads send real names
-   Vendored in urllib3

0.7.6 (2011-11-07)
------------------

-   Digest authentication bugfix (attach query data to path)

0.7.5 (2011-11-04)
------------------

-   Response.content = None if there was an invalid response.
-   Redirection auth handling.

0.7.4 (2011-10-26)
------------------

-   Session Hooks fix.

0.7.3 (2011-10-23)
------------------

-   Digest Auth fix.

0.7.2 (2011-10-23)
------------------

-   PATCH Fix.

0.7.1 (2011-10-23)
------------------

-   Move away from urllib2 authentication handling.
-   Fully Remove AuthManager, AuthObject, &c.
-   New tuple-based auth system with handler callbacks.

0.7.0 (2011-10-22)
------------------

-   Sessions are now the primary interface.
-   Deprecated InvalidMethodException.
-   PATCH fix.
-   New config system (no more global settings).

0.6.6 (2011-10-19)
------------------

-   Session parameter bugfix (params merging).

0.6.5 (2011-10-18)
------------------

-   Offline (fast) test suite.
-   Session dictionary argument merging.

0.6.4 (2011-10-13)
------------------

-   Automatic decoding of unicode, based on HTTP Headers.
-   New `decode_unicode` setting.
-   Removal of `r.read/close` methods.
-   New `r.faw` interface for advanced response usage.\*
-   Automatic expansion of parameterized headers.

0.6.3 (2011-10-13)
------------------

-   Beautiful `requests.async` module, for making async requests w/
    gevent.

0.6.2 (2011-10-09)
------------------

-   GET/HEAD obeys allow\_redirects=False.

0.6.1 (2011-08-20)
------------------

-   Enhanced status codes experience `\o/`
-   Set a maximum number of redirects (`settings.max_redirects`)
-   Full Unicode URL support
-   Support for protocol-less redirects.
-   Allow for arbitrary request types.
-   Bugfixes

0.6.0 (2011-08-17)
------------------

-   New callback hook system
-   New persistent sessions object and context manager
-   Transparent Dict-cookie handling
-   Status code reference object
-   Removed Response.cached
-   Added Response.request
-   All args are kwargs
-   Relative redirect support
-   HTTPError handling improvements
-   Improved https testing
-   Bugfixes

0.5.1 (2011-07-23)
------------------

-   International Domain Name Support!
-   Access headers without fetching entire body (`read()`)
-   Use lists as dicts for parameters
-   Add Forced Basic Authentication
-   Forced Basic is default authentication type
-   `python-requests.org` default User-Agent header
-   CaseInsensitiveDict lower-case caching
-   Response.history bugfix

0.5.0 (2011-06-21)
------------------

-   PATCH Support
-   Support for Proxies
-   HTTPBin Test Suite
-   Redirect Fixes
-   settings.verbose stream writing
-   Querystrings for all methods
-   URLErrors (Connection Refused, Timeout, Invalid URLs) are treated as
    explicitly raised
    `r.requests.get('hwe://blah'); r.raise_for_status()`

0.4.1 (2011-05-22)
------------------

-   Improved Redirection Handling
-   New 'allow\_redirects' param for following non-GET/HEAD Redirects
-   Settings module refactoring

0.4.0 (2011-05-15)
------------------

-   Response.history: list of redirected responses
-   Case-Insensitive Header Dictionaries!
-   Unicode URLs

0.3.4 (2011-05-14)
------------------

-   Urllib2 HTTPAuthentication Recursion fix (Basic/Digest)
-   Internal Refactor
-   Bytes data upload Bugfix

0.3.3 (2011-05-12)
------------------

-   Request timeouts
-   Unicode url-encoded data
-   Settings context manager and module

0.3.2 (2011-04-15)
------------------

-   Automatic Decompression of GZip Encoded Content
-   AutoAuth Support for Tupled HTTP Auth

0.3.1 (2011-04-01)
------------------

-   Cookie Changes
-   Response.read()
-   Poster fix

0.3.0 (2011-02-25)
------------------

-   Automatic Authentication API Change
-   Smarter Query URL Parameterization
-   Allow file uploads and POST data together
-

    New Authentication Manager System

    :   -   Simpler Basic HTTP System
        -   Supports all built-in urllib2 Auths
        -   Allows for custom Auth Handlers

0.2.4 (2011-02-19)
------------------

-   Python 2.5 Support
-   PyPy-c v1.4 Support
-   Auto-Authentication tests
-   Improved Request object constructor

0.2.3 (2011-02-15)
------------------

-

    New HTTPHandling Methods

    :   -   Response.\_\_nonzero\_\_ (false if bad HTTP Status)
        -   Response.ok (True if expected HTTP Status)
        -   Response.error (Logged HTTPError if bad HTTP Status)
        -   Response.raise\_for\_status() (Raises stored HTTPError)

0.2.2 (2011-02-14)
------------------

-   Still handles request in the event of an HTTPError. (Issue \#2)
-   Eventlet and Gevent Monkeypatch support.
-   Cookie Support (Issue \#1)

0.2.1 (2011-02-14)
------------------

-   Added file attribute to POST and PUT requests for multipart-encode
    file uploads.
-   Added Request.url attribute for context and redirects

0.2.0 (2011-02-14)
------------------

-   Birth!

0.0.1 (2011-02-13)
------------------

-   Frustration
-   Conception

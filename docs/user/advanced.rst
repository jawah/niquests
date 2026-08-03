.. _advanced:

Advanced usage
==============

This document covers some of Niquests' more advanced features.

.. _session-objects:

Session objects
---------------

The Session object allows you to persist certain parameters across
requests. It also persists cookies across all requests made from the
Session instance and uses ``urllib3.future``'s `connection pooling`_. If you
are making several requests to the same host, the underlying TCP
connection will be reused, which can result in a significant performance
increase (see `HTTP persistent connection`_).

A Session object has all the methods of the main Niquests API.

The following examples persist cookies across requests:

.. tab:: 🔂 Sync

    .. code:: python

        s = niquests.Session()

        s.get('https://httpbingo.org/cookies/set?sessioncookie=123456789')
        r = s.get('https://httpbingo.org/cookies')

        print(r.json()['cookies'])
        # {'sessioncookie': '123456789'}

.. tab:: 🔀 Async

    .. code:: python

        s = niquests.AsyncSession()

        await s.get('https://httpbingo.org/cookies/set?sessioncookie=123456789')
        r = await s.get('https://httpbingo.org/cookies')

        print(r.json()['cookies'])
        # {'sessioncookie': '123456789'}

Sessions can also be used to provide default data to the request methods. This
is done by providing data to the properties on a Session object:

.. tab:: 🔂 Sync

    .. code:: python

        s = niquests.Session()
        s.auth = ('user', 'pass')
        s.headers.update({'x-test': 'true'})

        # both 'x-test' and 'x-test2' are sent
        s.get('https://httpbingo.org/headers', headers={'x-test2': 'true'})

.. tab:: 🔀 Async

    .. code:: python

        s = niquests.AsyncSession()
        s.auth = ('user', 'pass')
        s.headers.update({'x-test': 'true'})

        # both 'x-test' and 'x-test2' are sent
        await s.get('https://httpbingo.org/headers', headers={'x-test2': 'true'})

.. versionadded:: 3.19

    You may also pass these defaults directly to the constructor, in the same way as ``headers``::

        s = niquests.Session(
            params={'page': '1'},
            headers={'x-test': 'true'},
            cookies={'from-my': 'browser'},
            auth=('user', 'pass'),
            proxies={'https': 'http://localhost:3128'},
            verify=True,
            cert=None,
            allow_incoming_cookies=True,
        )

    A native :class:`~http.cookiejar.CookieJar` (or a plain mapping) given to
    ``cookies`` is silently converted to a
    :class:`~niquests.cookies.RequestsCookieJar`, so
    :attr:`s.cookies <niquests.Session.cookies>` always exposes the convenient mapping
    interface (e.g. :meth:`s.cookies.set(...) <niquests.cookies.RequestsCookieJar.set>`).


Any dictionaries that you pass to a request method will be merged with the
session-level values that are set. The method-level parameters override session
parameters.

Note, however, that method-level parameters will *not* be persisted across
requests, even if using a session. This example will only send the cookies
with the first request, but not the second:

.. tab:: 🔂 Sync

    .. code:: python

        s = niquests.Session()

        r = s.get('https://httpbingo.org/cookies', cookies={'from-my': 'browser'})
        print(r.json()['cookies'])
        # {'from-my': 'browser'}

        r = s.get('https://httpbingo.org/cookies')
        print(r.json()['cookies'])
        # {}

.. tab:: 🔀 Async

    .. code:: python

        s = niquests.AsyncSession()

        r = await s.get('https://httpbingo.org/cookies', cookies={'from-my': 'browser'})
        print(r.json()['cookies'])
        # {'from-my': 'browser'}

        r = await s.get('https://httpbingo.org/cookies')
        print(r.json()['cookies'])
        # {}

If you want to manually add cookies to your session, use the
:ref:`Cookie utility functions <api-cookies>` to manipulate
:attr:`Session.cookies <niquests.Session.cookies>`.

Sessions can also be used as context managers:

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session() as s:
            s.get('https://httpbingo.org/cookies/set?sessioncookie=123456789')

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as s:
            await s.get('https://httpbingo.org/cookies/set?sessioncookie=123456789')

This ensures that the session is closed as soon as the ``with`` block is
exited, even if unhandled exceptions occurred.


.. admonition:: Remove a Value From a Dict Parameter

    Sometimes you'll want to omit session-level keys from a dict parameter. To
    do this, you simply set that key's value to ``None`` in the method-level
    parameter. It will automatically be omitted.

All values that are contained within a session are directly available to you.
See the :ref:`Session API Docs <sessionapi>` to learn more.

The :class:`~niquests.Session` and :class:`~niquests.AsyncSession` constructors
accept the following optional keyword arguments:

- ``resolver``: A resolver URL, resolver description, resolver object, or list of
  resolver URLs or descriptions.
- ``source_address``: The local ``(address, port)`` used for outgoing connections.
- ``quic_cache_layer``: A mutable mapping used to retain Alt-Svc HTTP/3 capabilities.
- ``retries``: A retry count or :class:`~niquests.RetryConfiguration`.
- ``multiplexed``: Enable lazy, concurrent requests over HTTP/2 or HTTP/3.
- ``disable_http1``, ``disable_http2``, and ``disable_http3``: Disable negotiation
  for selected HTTP versions. Disabling HTTP/1 also enables h2c prior knowledge.
- ``disable_ipv6`` and ``disable_ipv4``: Exclude an address family. They cannot both
  be ``True``.
- ``pool_connections``: Maximum number of host pools retained by the session.
- ``pool_maxsize``: Maximum number of connections retained per host pool.
- ``happy_eyeballs``: Enable Happy Eyeballs, optionally with an integer concurrency limit.
- ``keepalive_delay``: How long to maintain HTTP/2 or HTTP/3 connections with PING
  frames. The default is 600 seconds.
- ``keepalive_idle_window``: Idle time before a keep-alive PING. The default is 60 seconds.
- ``base_url``: A URL prefix merged with relative request URLs.
- ``timeout``: A session-wide timeout override. ``None`` leaves request methods to
  use their defaults of 30 seconds for reads and 120 seconds for writes.
- ``headers``: Default request headers.
- ``auth``: Default authentication tuple, token, or authentication object.
- ``hooks``: A hook mapping or :class:`~niquests.hooks.LifeCycleHook`; asynchronous
  sessions also accept :class:`~niquests.hooks.AsyncLifeCycleHook` and coroutine hooks.
- ``revocation_configuration``: A :class:`~niquests.RevocationConfiguration`, or
  ``None`` to disable revocation checking.
- ``app``: A WSGI or ASGI application mounted automatically. Async sessions accept
  ASGI applications only.
- ``params``: Default query-string parameters.
- ``cookies``: Default outgoing cookies as a mapping or
  :class:`~http.cookiejar.CookieJar`.
- ``proxies``: Default proxy mapping.
- ``verify``: Default server-certificate verification policy, CA bundle path, CA PEM
  content, or certificate fingerprint.
- ``cert``: Default client-certificate path, PEM content, ``(certificate, key)``, or
  ``(certificate, key, password)``.
- ``allow_incoming_cookies``: Whether to extract response ``Set-Cookie`` headers into
  the session jar. This defaults to ``True``; ``False`` does not prevent explicitly
  configured outgoing cookies from being sent.
- ``tls_configuration``: A :class:`~niquests.TLSConfiguration` applied to mounted
  TLS-capable adapters.
- ``json_encoder``: A callable that serializes values passed through ``json=`` and
  returns :class:`str` or :class:`bytes`.

A custom JSON encoder can handle application-specific objects without pre-serializing
every request.

.. tab:: 🔂 Sync

    .. code:: python

        import json

        encoder = lambda value: json.dumps(value, default=str)
        with niquests.Session(json_encoder=encoder) as session:
            response = session.post(
                "https://httpbingo.org/post", json={"value": 1}
            )

.. tab:: 🔀 Async

    .. code:: python

        import json

        encoder = lambda value: json.dumps(value, default=str)
        async with niquests.AsyncSession(json_encoder=encoder) as session:
            response = await session.post(
                "https://httpbingo.org/post", json={"value": 1}
            )

The top-level request helpers and their asynchronous counterparts also accept
``json_encoder`` and ``tls_configuration``. These options configure the temporary
session created for that one call.

To send explicitly configured cookies but ignore all ``Set-Cookie`` response headers,
construct a session with ``allow_incoming_cookies=False``. The setting applies to direct
responses and redirect history; it does not remove cookies already in the jar::

    session = niquests.Session(
        cookies={"outgoing": "yes"},
        allow_incoming_cookies=False,
    )

Resolver objects and ownership
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passing a resolver URL or description makes the session instantiate and own the
resolver; closing the session closes that resolver. Passing an already instantiated
resolver object transfers no ownership: the caller remains responsible for closing it,
and it remains available after the session closes. Synchronous sessions require a
synchronous resolver object, while asynchronous sessions require its asynchronous
counterpart. Resolver descriptions are available as
:class:`~urllib3.contrib.resolver.factories.ResolverDescription` and
:class:`~urllib3.contrib.resolver._async.factories.AsyncResolverDescription` from
:mod:`niquests.packages.urllib3 <urllib3>`.

.. _request-and-response-objects:

Setting a base URL
------------------

.. note:: Available in version 3.11+

You can avoid repeated URL concatenation when a session targets one server or base path.
Configure it as follows:

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session(base_url="https://httpbingo.org") as s:
            s.get('/headers')  # internally will become "https://httpbingo.org/headers"

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession(base_url="https://httpbingo.org") as s:
            await s.get('/headers')  # internally will become "https://httpbingo.org/headers"

Overriding the scheme per request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: Available in version 3.19+

When a ``base_url`` is set, every request reuses its scheme. Sometimes you need to reach
the same host with a different scheme (e.g. an SSE or WebSocket endpoint) without retyping
the full URL. Pass ``override_scheme`` to any request method to swap the scheme of the final
(``base_url``-merged) URL, just before the adapter is picked.

It is only honored when a ``base_url`` is configured; otherwise you already control the full
URL (and its scheme), so it is ignored.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session(base_url="https://httpbingo.org") as s:
            # Internally targets "sse://httpbingo.org/sse".
            s.get('/sse', override_scheme="sse")

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession(base_url="https://httpbingo.org") as s:
            # Internally targets "sse://httpbingo.org/sse".
            await s.get('/sse', override_scheme="sse")

Request and Response objects
----------------------------

Each request method builds a :class:`~niquests.Request`, prepares and sends it, then
returns a :class:`~niquests.Response`. The response contains the server's status,
headers, and body, and its :attr:`~niquests.Response.request` attribute is the
:class:`~niquests.PreparedRequest` that was actually sent.

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.get('https://httpbingo.org/headers')
        print(response.headers['content-type'])
        print(response.request.method)
        print(response.request.headers['user-agent'])

.. tab:: 🔀 Async

    .. code:: python

        response = await niquests.aget('https://httpbingo.org/headers')
        print(response.headers['content-type'])
        print(response.request.method)
        print(response.request.headers['user-agent'])

.. _prepared-requests:

Prepared requests
-----------------

Whenever you receive a :class:`Response <niquests.Response>` object
from an API call or a Session call, the :attr:`~niquests.Response.request` attribute is actually the
:class:`~niquests.PreparedRequest` that was used. In some cases you may wish to do some extra
work to the body or headers (or anything else really) before sending a
request. The simple recipe for this is the following:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Request, Session

        s = Session()

        req = Request('POST', url, data=data, headers=headers)
        prepped = req.prepare()

        # do something with prepped.body
        prepped.body = 'No, I want exactly this as the body.'

        # do something with prepped.headers
        del prepped.headers['Content-Type']

        resp = s.send(prepped,
            stream=stream,
            verify=verify,
            proxies=proxies,
            cert=cert,
            timeout=timeout
        )

        print(resp.status_code)

.. tab:: 🔀 Async

    .. code:: python

        from niquests import Request, AsyncSession

        s = AsyncSession()

        req = Request('POST', url, data=data, headers=headers)
        prepped = req.prepare()

        # do something with prepped.body
        prepped.body = 'No, I want exactly this as the body.'

        # do something with prepped.headers
        del prepped.headers['Content-Type']

        resp = await s.send(prepped,
            stream=stream,
            verify=verify,
            proxies=proxies,
            cert=cert,
            timeout=timeout
        )

        print(resp.status_code)

When no session state is needed, prepare the :class:`~niquests.Request` immediately and
modify the resulting :class:`~niquests.PreparedRequest`. Then
send that with the other parameters you would have sent to ``niquests.*`` or
``Session.*``.

However, the above code loses some of the advantages of using a Niquests
:class:`Session <niquests.Session>` object. In particular,
:class:`Session <niquests.Session>`-level state such as cookies will
not get applied to your request. To get a
:class:`PreparedRequest <niquests.PreparedRequest>` with that state
applied, replace the call to :meth:`Request.prepare()
<niquests.Request.prepare>` with a call to
:meth:`Session.prepare_request() <niquests.Session.prepare_request>`, like this:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Request, Session

        s = Session()
        req = Request('GET',  url, data=data, headers=headers)

        prepped = s.prepare_request(req)

        # do something with prepped.body
        prepped.body = 'Seriously, send exactly these bytes.'

        # do something with prepped.headers
        prepped.headers['X-Debug'] = 'enabled'

        resp = s.send(prepped,
            stream=stream,
            verify=verify,
            proxies=proxies,
            cert=cert,
            timeout=timeout
        )

        print(resp.status_code)

.. tab:: 🔀 Async

    .. code:: python

        from niquests import Request, AsyncSession

        s = AsyncSession()
        req = Request('GET',  url, data=data, headers=headers)

        prepped = s.prepare_request(req)

        # do something with prepped.body
        prepped.body = 'Seriously, send exactly these bytes.'

        # do something with prepped.headers
        prepped.headers['X-Debug'] = 'enabled'

        resp = await s.send(prepped,
            stream=stream,
            verify=verify,
            proxies=proxies,
            cert=cert,
            timeout=timeout
        )

        print(resp.status_code)

When using the prepared-request flow, keep in mind that :meth:`~niquests.Session.send`
does not merge environment settings automatically. This can cause problems when
environment variables configure Niquests. For example, a CA bundle specified in
``REQUESTS_CA_BUNDLE`` is otherwise ignored, which can cause certificate verification
to fail. Explicitly merge the environment settings into your session:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Request, Session

        s = Session()
        req = Request('GET', url)

        prepped = s.prepare_request(req)

        # Merge environment settings into session
        settings = s.merge_environment_settings(prepped.url, {}, None, None, None)
        resp = s.send(prepped, **settings)

        print(resp.status_code)

.. tab:: 🔀 Async

    .. code:: python

        from niquests import Request, AsyncSession

        s = AsyncSession()
        req = Request('GET', url)

        prepped = s.prepare_request(req)

        # Merge environment settings into session
        settings = s.merge_environment_settings(prepped.url, {}, None, None, None)
        resp = await s.send(prepped, **settings)

        print(resp.status_code)

.. _verification:

TLS certificate verification
----------------------------

Niquests verifies TLS certificates for HTTPS requests, like a web browser. Verification
is enabled by default, and Niquests raises :class:`~niquests.exceptions.SSLError` when
it cannot verify a certificate. A normally configured public endpoint succeeds::

    >>> niquests.get('https://github.com').status_code
    200

You can pass ``verify`` the path to a CA_BUNDLE file or directory with certificates of trusted CAs::

    >>> niquests.get('https://github.com', verify='/path/to/certfile')

To persist the setting::

    s = niquests.Session()
    s.verify = '/path/to/certfile'

.. note:: If ``verify`` is set to a path to a directory, the directory must have been processed using
  the ``c_rehash`` utility supplied with OpenSSL.

This list of trusted CAs can also be specified through the ``REQUESTS_CA_BUNDLE`` environment variable.
If ``REQUESTS_CA_BUNDLE`` is not set, ``CURL_CA_BUNDLE`` is used as a fallback.

Niquests can skip TLS certificate verification when ``verify=False``::

    response = niquests.get('https://localhost:8443', verify=False)

Note that when ``verify`` is set to ``False``, requests will accept any TLS
certificate presented by the server, and will ignore hostname mismatches
and/or expired certificates, which will make your application vulnerable to
man-in-the-middle (MitM) attacks. Use this only in controlled local testing.

By default, ``verify`` is ``True``. It controls server certificates, not client certificates.

Client certificates
-------------------

You can also specify a local certificate to use as a client certificate, as a single
file (containing the private key and the certificate) or as a tuple of both
files' paths::

    response = niquests.get(
        'https://service.example',
        cert=('/path/client.cert', '/path/client.key'),
    )

or persistent::

    s = niquests.Session()
    s.cert = '/path/client.cert'

If you specify a wrong path or an invalid certificate, Niquests raises
:class:`~niquests.exceptions.SSLError`::

    >>> niquests.get('https://service.example', cert='/wrong_path/client.pem')
    SSLError: [Errno 336265225] _ssl.c:347: error:140B0009:SSL routines:SSL_CTX_use_PrivateKey_file:PEM lib

.. warning:: The private key must be unencrypted unless you supply its passphrase.

You may specify the private key passphrase using the following example::

    response = niquests.get(
        'https://service.example',
        cert=('/path/client.cert', '/path/client.key', 'my_key_password'),
    )

DNS with mTLS
~~~~~~~~~~~~~

You can pass a client certificate to authenticate to a DNS resolver::

    from niquests.packages.urllib3 import ResolverDescription
    from niquests import Session

    rd = ResolverDescription.from_url("doq://my-resolver.tld")
    rd["cert_data"] = certificate_pem
    rd["key_data"] = private_key_pem
    rd["key_password"] = ...

    with Session(resolver=rd) as s:
        ...

.. note:: Instead of in-memory PEM content, use ``cert_file`` and ``key_file`` for paths.

This method of authentication is broadly used with DNS over TLS, QUIC, and HTTPS.

In-memory certificates
----------------------

Both ``verify`` and ``cert`` accept PEM content in memory. For ``verify``, pass a
:class:`str` or :class:`bytes` containing one or more CA certificates. For mTLS, pass either a
single :class:`str` containing the client certificate and private key, a
``(certificate_pem, private_key_pem)`` tuple, or a
``(certificate_pem, private_key_pem, password)`` tuple. A plain string without a PEM
certificate marker is interpreted as a file path.

.. _ca-certificates:

CA certificates
---------------

Niquests obtains its default CA certificates through `wassima`_. It prefers the
operating system trust store when the platform exposes one. If no system roots
are accessible, wassima falls back to its embedded bundle derived from the
Common CA Database (CCADB), rather than ``certifi``.

On Linux and BSD systems, wassima also detects a system trust store that has not
been updated in the last three years. In that case, it augments the stale system
roots with its embedded CCADB bundle so recently added public roots remain
available.

.. _tls-configuration:

TLS configuration
-----------------

.. versionadded:: 3.20.0

For finer control over TLS, pass a :class:`~niquests.TLSConfiguration` to a session or
top-level request. It can select a TLS backend, constrain protocol versions, configure
ciphers, and control hostname assertions.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests
        from niquests.packages.urllib3.contrib.anytls import ssl

        tls_config = niquests.TLSConfiguration(
            backend="ssl",  # "ssl", "utls", or "rtls"
            min_version=ssl.TLSVersion.TLSv1_2,
            max_version=ssl.TLSVersion.TLSv1_3,
            ciphers=None,
            assert_hostname=None,  # Verify the request hostname normally.
        )

        with niquests.Session(tls_configuration=tls_config) as session:
            response = session.get("https://one.one.one.one")

        response = niquests.get(
            "https://one.one.one.one",
            tls_configuration=tls_config,
        )

.. tab:: 🔀 Async

    .. code:: python

        import niquests
        from niquests.packages.urllib3.contrib.anytls import ssl

        tls_config = niquests.TLSConfiguration(
            backend="ssl",
            min_version=ssl.TLSVersion.TLSv1_2,
            max_version=ssl.TLSVersion.TLSv1_3,
            assert_hostname=None,
        )

        async with niquests.AsyncSession(tls_configuration=tls_config) as session:
            response = await session.get("https://one.one.one.one")

        response = await niquests.aget(
            "https://one.one.one.one",
            tls_configuration=tls_config,
        )

Every field is optional; ``None`` retains the backend default. Setting
``assert_hostname=False`` disables hostname matching while certificate-chain
verification may remain enabled. This weakens identity verification and permits a
valid certificate for the wrong host, enabling MitM attacks. Do not disable hostname
assertion in production. Leave ``assert_hostname=None`` to verify the request hostname normally.

.. note:: Selecting ``backend`` requires urllib3.future 2.22.900 or later. With an
   older version, that setting is ignored with a warning; all other options remain effective.

.. _HTTP persistent connection: https://en.wikipedia.org/wiki/HTTP_persistent_connection
.. _connection pooling: https://urllib3.readthedocs.io/en/latest/reference/index.html#module-urllib3.connectionpool
.. _wassima: https://github.com/jawah/wassima
.. _body-content-workflow:

Body content workflow
---------------------

By default, when you make a request, the body of the response is downloaded
immediately. You can override this behaviour and defer downloading the response
body until you access the :attr:`Response.content <niquests.Response.content>`
attribute with the ``stream`` parameter:

.. tab:: 🔂 Sync

    .. code:: python

        tarball_url = 'https://github.com/jawah/niquests/tarball/main'
        r = niquests.get(tarball_url, stream=True)

.. tab:: 🔀 Async

    .. code:: python

        tarball_url = 'https://github.com/jawah/niquests/tarball/main'
        async with niquests.AsyncSession() as s:
            r = await s.get(tarball_url, stream=True)

At this point only the response headers have been downloaded and the connection
remains open, allowing content retrieval to be conditional.

.. tab:: 🔂 Sync

    .. code:: python

        if int(r.headers.get('content-length', 0)) < TOO_LONG:
            content = r.content

.. tab:: 🔀 Async

    .. code:: python

        if int(r.headers.get('content-length', 0)) < TOO_LONG:
            content = await r.content

You can further control the workflow by use of the :meth:`Response.iter_content() <niquests.Response.iter_content>`
and :meth:`Response.iter_lines() <niquests.Response.iter_lines>` methods.
Alternatively, you can read the undecoded body from the underlying
urllib3 :class:`urllib3.HTTPResponse <urllib3.response.HTTPResponse>` at
:attr:`Response.raw <niquests.Response.raw>`.

If you set ``stream`` to ``True`` when making a request, Niquests cannot
release the connection back to the pool unless you consume all the data (HTTP/1.1 only) or call
:meth:`Response.close <niquests.Response.close>`. This can lead to
inefficiency with connections. If you find yourself partially reading request
bodies (or not reading them at all) while using ``stream=True``, you should
make the request within a context manager to ensure it is always closed.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.get('https://httpbingo.org/get', stream=True) as r:
            for chunk in r.iter_content(8192):
                process(chunk)

        r = niquests.get('https://httpbingo.org/get', stream=True)
        try:
            content = r.content
        finally:
            r.close()

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as session:
            async with await session.get(
                'https://httpbingo.org/get', stream=True
            ) as r:
                async for chunk in await r.iter_content(8192):
                    process(chunk)

            r = await session.get('https://httpbingo.org/get', stream=True)
            try:
                content = await r.content
            finally:
                await r.close()

.. _keep-alive:

Keep-alive
----------

Thanks to urllib3.future, persistent connections are automatic within a session.
Requests reuse an appropriate available connection.

Note that connections are only released back to the pool for reuse once all body
data has been read; be sure to either set ``stream`` to ``False`` or read the
:attr:`~niquests.Response.content` property of the :class:`~niquests.Response` object.

.. versionadded:: 3.10
   Before this, only HTTP/1.1 connections were kept alive properly.

Niquests can maintain an HTTP connection with a scheduled task for each host,
regardless of the negotiated protocol.

.. tab:: 🔂 Sync

    .. code-block:: python

        import niquests

        sess = niquests.Session(keepalive_delay=600, keepalive_idle_window=60)

.. tab:: 🔀 Async

    .. code-block:: python

        import niquests

        sess = niquests.AsyncSession(keepalive_delay=600, keepalive_idle_window=60)

These defaults maintain a connection for 10 minutes and send PING frames after 60
seconds of inactivity.

PING frames are sent only over HTTP/2 or HTTP/3. Any connection activity, including
unsolicited incoming data, resets the idle window.

.. note:: Setting either ``keepalive_delay`` or ``keepalive_idle_window`` to ``None``
   disables this feature.

.. warning:: Do not set ``keepalive_idle_window`` below 30 seconds. Values below one
   second are clamped to one second. Frequent PING frames reduce pool performance and
   may cause the server to close the connection.

After ``keepalive_delay`` elapses, Niquests does not close the connection; it only stops
sending keep-alive PING frames. A server may retain that connection for longer.

.. _streaming-uploads:

Streaming uploads
-----------------

Niquests supports streaming uploads, which allow you to send large streams or
files without reading them into memory. To stream and upload, simply provide a
file-like object for your body:

.. tab:: 🔂 Sync

    .. code:: python

        with open('massive-body', 'rb') as f:
            niquests.post('https://httpbingo.org/post', data=f)

.. tab:: 🔀 Async

    .. code:: python

        import aiofile

        async with aiofile.async_open('massive-body', 'rb') as f:
            await niquests.apost('https://httpbingo.org/post', data=f)

.. warning:: It is recommended that you open files in binary mode.

Async streaming uploads
-----------------------

Because file I/O can block for significant periods, asynchronous upload is recommended.

Niquests supports files opened with ``aiofile``.

.. code:: python

    import niquests
    import asyncio
    import aiofile

    async def upload() -> None:
        async with niquests.AsyncSession() as s:
            async with aiofile.async_open("massive-body", "rb") as afp:
                r = await s.post("https://httpbingo.org/post", data=afp)

    if __name__ == "__main__":
        asyncio.run(upload())

.. tip:: Any compatible asynchronous file manager may be used. This example uses
   ``aiofile``; see https://pypi.org/project/aiofile/.

.. _chunk-encoding:

Chunk-encoded requests
----------------------

Niquests also supports chunked transfer encoding for outgoing requests and incoming responses.
To send a chunk-encoded request, simply provide a generator (or any iterator without
a length) for your body:

.. tab:: 🔂 Sync

    .. code:: python

        def gen():
            yield 'hi'
            yield 'there'

        niquests.post('https://httpbingo.org/post', data=gen())

.. tab:: 🔀 Async

    .. code:: python

        async def gen():
            yield 'hi'
            yield 'there'

        await niquests.apost('https://httpbingo.org/post', data=gen())

For chunked responses, iterate over the data using
:meth:`Response.iter_content() <niquests.Response.iter_content>`. In
an ideal situation you'll have set ``stream=True`` on the request, in which
case you can iterate chunk-by-chunk by calling
:meth:`~niquests.Response.iter_content` with a ``chunk_size``
parameter of ``None``. To request a maximum read size, set ``chunk_size`` to an integer.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.get(url, stream=True) as response:
            for chunk in response.iter_content(chunk_size=None):
                process(chunk)

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as session:
            async with await session.get(url, stream=True) as response:
                async for chunk in await response.iter_content(chunk_size=None):
                    process(chunk)

.. note:: Since Niquests v3.7.1+ we support having async iterable passed down to ``data=...`` via your :class:`~niquests.AsyncSession`.

.. _multipart:

POST multiple multipart-encoded files
-------------------------------------

You can send multiple files in one request. For example, suppose you want to
upload image files to an HTML form with a multiple file field 'images'::

    <input type="file" name="images" multiple="true" required="true"/>

Set ``files`` to a list of ``(form_field_name, file_info)`` tuples. The in-memory
streams below keep the example self-contained; use context managers to close real files.

.. tab:: 🔂 Sync

    .. code:: python

        from io import BytesIO

        with BytesIO(b'first image') as first, BytesIO(b'second image') as second:
            multiple_files = [
                ('images', ('foo.png', first, 'image/png')),
                ('images', ('bar.png', second, 'image/png')),
            ]
            response = niquests.post('https://httpbingo.org/post', files=multiple_files)

.. tab:: 🔀 Async

    .. code:: python

        from io import BytesIO

        async with niquests.AsyncSession() as session:
            with BytesIO(b'first image') as first, BytesIO(b'second image') as second:
                multiple_files = [
                    ('images', ('foo.png', first, 'image/png')),
                    ('images', ('bar.png', second, 'image/png')),
                ]
                response = await session.post(
                    'https://httpbingo.org/post', files=multiple_files
                )

.. warning:: It is recommended that you open files in binary
             mode. Errors may occur if you open the file in *text mode*.
             Multipart encoding requires byte-accurate lengths and content.


.. _event-hooks:

Event hooks
-----------

Niquests has a hook system that you can use to manipulate portions of
the request process, or signal event handling.

Available hooks:

``early_response``:
    An informational response received before the final response, such as 103 Early Hints.
``response``:
    The final :class:`~niquests.Response`.
``pre_send``:
    The :class:`~niquests.PreparedRequest` after a live connection is selected and
    :attr:`~niquests.PreparedRequest.conn_info` is populated. Do not mutate the request
    at this stage.
``on_upload``:
    The prepared request whenever a body block is transmitted. Its
    :attr:`~niquests.PreparedRequest.upload_progress` tracks the transfer. Keep this hook inexpensive.
``pre_request``:
    The newly built prepared request, which may be modified before transmission.

You can assign a hook function on a per-request basis by passing a
``{hook_name: callback_function}`` dictionary to the ``hooks`` request
parameter::

    hooks={'response': print_url}

The callback receives the event object as its first argument and may also receive
event-specific keyword arguments. Accept ``**kwargs`` for forward compatibility.

::

    def print_url(r, *args, **kwargs):
        print(r.url)

Unhandled callback exceptions propagate to the caller.

If the callback function returns a value, it is assumed that it is to
replace the data that was passed in. If the function doesn't return
anything, nothing else is affected.

::

    def record_hook(r, *args, **kwargs):
        r.hook_called = True
        return r

Let's print some request method arguments at runtime::

    >>> niquests.get('https://httpbingo.org/', hooks={'response': print_url})
    https://httpbingo.org/
    <Response HTTP/2 [200]>

You can add multiple hooks to a single request::

    >>> r = niquests.get('https://httpbingo.org/', hooks={'response': [print_url, record_hook]})
    >>> r.hook_called
    True

You can also add hooks to a :class:`~niquests.Session` instance.  Any hooks you add will then
be called on every request made to the session.  For example::

   >>> s = niquests.Session()
   >>> s.hooks['response'].append(print_url)
   >>> s.get('https://httpbingo.org/')
    https://httpbingo.org/
    <Response HTTP/2 [200]>

A :class:`~niquests.Session` can have multiple hooks, which will be called in the order
they are added.

Retrieve connection information immediately before a request is sent:

.. tab:: 🔂 Sync

    .. code:: python

        def print_connection(request, **kwargs):
            print(request.conn_info)

        response = niquests.get(
            "https://one.one.one.one",
            hooks={"pre_send": [print_connection]},
        )

.. tab:: 🔀 Async

    .. code:: python

        async def print_connection(request, **kwargs):
            print(request.conn_info)

        async with niquests.AsyncSession() as session:
            response = await session.get(
                "https://one.one.one.one",
                hooks={"pre_send": [print_connection]},
            )

Here, ``r`` is the :class:`~niquests.PreparedRequest` and
:attr:`~niquests.PreparedRequest.conn_info` contains a
:class:`~urllib3.backend._base.ConnectionInfo`.
You can explore the following data in it.

- **certificate_der**: The peer certificate in DER format (binary)
- **certificate_dict**: The peer certificate as returned by
  :meth:`ssl.SSLSocket.getpeercert(binary_form=False) <ssl.SSLSocket.getpeercert>`.
- **tls_version**: TLS version.
- **cipher**: Cipher used.
- **http_version**: HTTP version that is about to be used.
- **destination_address**: The remote peer address given to us by the DNS resolver.
- **issuer_certificate_der**: Immediate issuer (in the TLS certificate chain) in DER format (binary)
- **issuer_certificate_dict**: Immediate issuer (in the TLS certificate chain) as a dictionary
- **established_latency**: The amount of time consumed to get an ESTABLISHED network link.
- **resolution_latency**: The amount of time consumed for the hostname resolution.
- **tls_handshake_latency**: The amount of time consumed for the TLS handshake completion.
- **request_sent_latency**: The amount of time consumed to encode and send the whole request through the socket.

.. warning:: Depending on the platform and interpreter, some values may always be
   ``None``. For example,
   :attr:`~urllib3.backend._base.ConnectionInfo.certificate_dict` may be unavailable on macOS.

Typical uses include displaying connection diagnostics in command-line applications,
collecting telemetry, and debugging transport behavior.

.. note:: :class:`~niquests.AsyncSession` accepts both synchronous callbacks and
   coroutine functions. :class:`~niquests.Session` accepts synchronous callbacks only.

Class-based hooks
-----------------

.. versionadded:: 3.16.0

In addition to dictionary-based hooks, Niquests supports class-based hooks via :class:`~niquests.hooks.LifeCycleHook` and :class:`~niquests.hooks.AsyncLifeCycleHook`. This approach allows for stateful middleware, better organization of logic, and easy composition of multiple hooks.

.. note:: They behave like the regular hooks you are accustomed to, and in addition to that, they can have a persistent (shared) state and easier proper typing annotation.

.. autoclass:: niquests.hooks.LifeCycleHook
    :members: pre_request, pre_send, on_upload, early_response, response

.. autoclass:: niquests.hooks.AsyncLifeCycleHook
    :members: pre_request, pre_send, on_upload, early_response, response

Single middleware
~~~~~~~~~~~~~~~~~

You can define a custom middleware by subclassing :class:`~niquests.hooks.AsyncLifeCycleHook` (or :class:`~niquests.hooks.LifeCycleHook` for synchronous contexts) and overriding the specific event methods you need.

.. code-block:: python

    import asyncio
    from niquests import AsyncSession, AsyncLifeCycleHook

    class ConnectionLogger(AsyncLifeCycleHook):
        async def pre_send(self, prepared_request, **kwargs) -> None:
            # Inspect the connection info before the request is sent
            print(f"Connected to: {prepared_request.conn_info}")

    async def main():
        async with AsyncSession() as s:
            # Pass an instance of your hook class
            await s.get("https://one.one.one.one", hooks=ConnectionLogger())

    if __name__ == "__main__":
        asyncio.run(main())

Combining middleware
~~~~~~~~~~~~~~~~~~~~

Middleware classes can be combined using the ``+`` operator. This allows you to chain multiple hooks together, mixing synchronous and asynchronous logic. They are executed in the order they are added.

.. code-block:: python

    import asyncio
    import typing
    from niquests import AsyncSession, AsyncLifeCycleHook, LifeCycleHook, Response

    class RequestTracer(AsyncLifeCycleHook):
        async def pre_send(self, prepared_request, **kwargs) -> None:
            print(f"[Trace] Sending request to {prepared_request.url}")

    class ResponseModifier(AsyncLifeCycleHook):
        async def response(self, response: Response, **kwargs: typing.Any) -> Response | None:
            print(f"[Mod] Received response with status {response.status_code}")
            return response

    class SyncAuditLog(LifeCycleHook):
        def pre_send(self, prepared_request, **kwargs) -> None:
            print("[Audit] Sync check triggered", prepared_request.conn_info)

    async def main():
        # Combine: Tracer -> Modifier -> Audit
        # The hooks will be executed in this sequence for every event they implement.
        middleware_chain = RequestTracer() + ResponseModifier() + SyncAuditLog()

        async with AsyncSession() as s:
            await s.get("https://one.one.one.one", hooks=middleware_chain)

    if __name__ == "__main__":
        asyncio.run(main())


.. danger:: In synchronous multithreaded code, shared
   :class:`~niquests.hooks.LifeCycleHook` state must be thread-safe. Use appropriate
   locking when mutating shared state.

Rate limiting
~~~~~~~~~~~~~

Niquests provides built-in rate limiters based on common algorithms. These are implemented as lifecycle hooks and can be passed directly to your session.

**Leaky Bucket Limiter**

Requests "leak" out at a constant rate. When a request arrives, it waits until enough time has passed since the last request to maintain the rate. This provides smooth, evenly-spaced requests.

.. tab:: 🔂 Sync

    .. code-block:: python

        import niquests

        limiter = niquests.LeakyBucketLimiter(rate=10.0)  # 10 requests per second
        with niquests.Session(hooks=limiter) as session:
            for i in range(20):
                session.get("https://httpbingo.org/get")  # Requests are evenly spaced

.. tab:: 🔀 Async

    .. code-block:: python

        import asyncio
        import niquests

        async def main():
            limiter = niquests.AsyncLeakyBucketLimiter(rate=10.0)
            async with niquests.AsyncSession(hooks=limiter) as session:
                for i in range(20):
                    await session.get("https://httpbingo.org/get")

        asyncio.run(main())

.. note:: These rate limiters are proactive - they throttle requests before they are sent. If the API still returns a 429 (Too Many Requests), consider using :class:`~niquests.RetryConfiguration` with ``status_forcelist=[429]`` and ``respect_retry_after_header=True`` for reactive retry handling.

**Token Bucket Limiter**

Tokens are added to a bucket at a constant rate up to a maximum capacity. Each request consumes one token. This allows bursts up to the bucket capacity while maintaining a long-term rate limit.

.. tab:: 🔂 Sync

    .. code-block:: python

        import niquests

        # Allows bursts of up to 50 requests, refills at 10/s
        limiter = niquests.TokenBucketLimiter(rate=10.0, capacity=50.0)
        with niquests.Session(hooks=limiter) as session:
            # First 50 requests can be immediate (burst)
            # After that, limited to 10 requests per second
            for i in range(100):
                session.get("https://httpbingo.org/get")

.. tab:: 🔀 Async

    .. code-block:: python

        import asyncio
        import niquests

        async def main():
            limiter = niquests.AsyncTokenBucketLimiter(rate=10.0, capacity=50.0)
            async with niquests.AsyncSession(hooks=limiter) as session:
                tasks = [session.get("https://httpbingo.org/get") for _ in range(100)]
                await asyncio.gather(*tasks)

        asyncio.run(main())

**Choosing Between Algorithms**

- Use **LeakyBucketLimiter** when you need smooth, evenly-spaced requests (e.g., polling an API).
- Use **TokenBucketLimiter** when you want to allow bursts while respecting a long-term rate (e.g., batch operations with quiet periods).

**Combining with Retry**

Rate limiters are proactive (throttle before sending), while :class:`~niquests.RetryConfiguration` is reactive (retry after failure). You can combine both for robust rate limit handling:

.. tab:: 🔂 Sync

    .. code-block:: python

        import niquests

        # Proactive: limit to 10 requests/second
        limiter = niquests.LeakyBucketLimiter(rate=10.0)

        # Reactive: retry on 429 with Retry-After header
        retry = niquests.RetryConfiguration(
            total=3,
            status_forcelist=[429],
            respect_retry_after_header=True,
        )

        with niquests.Session(hooks=limiter, retries=retry) as session:
            for i in range(100):
                session.get("https://api.example.com/data")

.. tab:: 🔀 Async

    .. code-block:: python

        import asyncio
        import niquests

        async def main():
            limiter = niquests.AsyncLeakyBucketLimiter(rate=10.0)
            retry = niquests.RetryConfiguration(
                total=3,
                status_forcelist=[429],
                respect_retry_after_header=True,
            )

            async with niquests.AsyncSession(hooks=limiter, retries=retry) as session:
                for i in range(100):
                    await session.get("https://api.example.com/data")

        asyncio.run(main())

Track upload progress
---------------------

You may use the ``on_upload`` hook to track the upload progress of a request.
The callable receives a :class:`~niquests.PreparedRequest` with an
:attr:`~niquests.PreparedRequest.upload_progress` property.

.. note:: :attr:`~niquests.PreparedRequest.upload_progress` is a
   :class:`~niquests.models.TransferProgress` instance.

For example:

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        def track(req):
            print(req.upload_progress)

        with niquests.Session() as s:
            s.post("https://httpbingo.org/post", data=b"foo" * 350_000, hooks={"on_upload": [track]})

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        async def track(req):
            print(req.upload_progress)

        async with niquests.AsyncSession() as s:
            await s.post("https://httpbingo.org/post", data=b"foo" * 350_000, hooks={"on_upload": [track]})

.. note:: The ``tqdm`` library can render this information as a progress bar.

:attr:`~niquests.PreparedRequest.upload_progress` contains the following properties:


- **percentage** (optional): Percentage expressed as a float from 0 to 100.
- **content_length** (optional): Expected byte count; it may be unset for iterators.
- **total**: Number of bytes sent to the remote peer.
- **is_completed**: Whether the transfer ended.
- **any_error**: Whether an error occurred during the transfer, including an early response.

.. _custom-auth:

Custom authentication
---------------------

Niquests allows you to specify your own authentication mechanism.

Any callable which is passed as the ``auth`` argument to a request method will
have the opportunity to modify the request before it is dispatched.

Synchronous authentication implementations subclass
:class:`AuthBase <niquests.auth.AuthBase>`; asynchronous implementations subclass
:class:`~niquests.auth.AsyncAuthBase`. Niquests provides two common authentication
scheme implementations in :mod:`niquests.auth`:
:class:`HTTPBasicAuth <niquests.auth.HTTPBasicAuth>` and
:class:`HTTPDigestAuth <niquests.auth.HTTPDigestAuth>`.

The following implementations attach an application token header.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests.auth import AuthBase

        class TokenAuth(AuthBase):
            def __init__(self, token):
                self.token = token

            def __call__(self, request):
                request.headers['X-Application-Token'] = self.token
                return request

        response = niquests.get(
            'https://httpbingo.org/headers', auth=TokenAuth('example-token')
        )

.. tab:: 🔀 Async

    .. code:: python

        from niquests.auth import AsyncAuthBase

        class TokenAuth(AsyncAuthBase):
            def __init__(self, token):
                self.token = token

            async def __call__(self, request):
                request.headers['X-Application-Token'] = self.token
                return request

        async with niquests.AsyncSession() as session:
            response = await session.get(
                'https://httpbingo.org/headers', auth=TokenAuth('example-token')
            )

.. note:: To send a Bearer token, pass the token string directly as ``auth=...``.

.. _streaming-requests:

Streaming requests
------------------

With :meth:`Response.iter_lines() <niquests.Response.iter_lines>` you can easily
iterate over streaming APIs such as the `Twitter Streaming
API <https://dev.twitter.com/streaming/overview>`_. Simply
set ``stream`` to ``True`` and iterate over the response with
:meth:`~niquests.Response.iter_lines()`:

.. tab:: 🔂 Sync

    .. code:: python

        import json
        import niquests

        r = niquests.get('https://httpbingo.org/stream/20', stream=True)

        for line in r.iter_lines():

            # filter out keep-alive new lines
            if line:
                decoded_line = line.decode('utf-8')
                print(json.loads(decoded_line))

.. tab:: 🔀 Async

    .. code:: python

        import json
        import niquests

        async with niquests.AsyncSession() as s:
            r = await s.get('https://httpbingo.org/stream/20', stream=True)

            async for line in r.iter_lines():

                # filter out keep-alive new lines
                if line:
                    decoded_line = line.decode('utf-8')
                    print(json.loads(decoded_line))

When using `decode_unicode=True` with
:meth:`Response.iter_lines() <niquests.Response.iter_lines>` or
:meth:`Response.iter_content() <niquests.Response.iter_content>`, you'll want
to provide a fallback encoding in the event the server doesn't provide one:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.get('https://httpbingo.org/stream/20', stream=True)

        if r.encoding is None:
            r.encoding = 'utf-8'

        for line in r.iter_lines(decode_unicode=True):
            if line:
                print(json.loads(line))

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as s:
            r = await s.get('https://httpbingo.org/stream/20', stream=True)

            if r.encoding is None:
                r.encoding = 'utf-8'

            async for line in r.iter_lines(decode_unicode=True):
                if line:
                    print(json.loads(line))

.. warning::

    :meth:`~niquests.Response.iter_lines()` is not reentrant safe.
    Calling this method multiple times causes some of the received data
    being lost. In case you need to call it from multiple places, use
    the resulting iterator object instead::

        lines = r.iter_lines()
        # Save the first line for later or just skip it

        first_line = next(lines)

        for line in lines:
            print(line)

.. _proxies:

Proxies
-------

If you need to use a proxy, configure individual requests with ``proxies``.

.. tab:: 🔂 Sync

    .. code:: python

        proxies = {
            'http': 'http://10.10.1.10:3128',
            'https': 'http://10.10.1.10:1080',
        }
        niquests.get('http://example.org', proxies=proxies)

.. tab:: 🔀 Async

    .. code:: python

        proxies = {
            'http': 'http://10.10.1.10:3128',
            'https': 'http://10.10.1.10:1080',
        }
        await niquests.aget('http://example.org', proxies=proxies)

Alternatively you can configure it once for an entire
:class:`Session <niquests.Session>`::

    import niquests

    proxies = {
      'http': 'http://10.10.1.10:3128',
      'https': 'http://10.10.1.10:1080',
    }
    session = niquests.Session()
    session.proxies.update(proxies)

    session.get('http://example.org')

.. warning:: Setting :attr:`session.proxies <niquests.Session.proxies>` may behave differently than expected.
    Values provided will be overwritten by environmental proxies
    (those returned by `urllib.request.getproxies <https://docs.python.org/3/library/urllib.request.html#urllib.request.getproxies>`_).
    To ensure the use of proxies in the presence of environmental proxies,
    explicitly specify the ``proxies`` argument on all individual requests as
    initially explained above.

    See `#2018 <https://github.com/psf/requests/issues/2018>`_ for details.

.. note:: This section also applies to WebSockets. By default, ``wss://`` uses the
   ``https`` proxy and ``ws://`` uses the ``http`` proxy. Add a ``wss`` or ``ws`` key
   to route either scheme differently.

When the proxies configuration is not overridden per request as shown above,
Niquests relies on the proxy configuration defined by standard
environment variables ``http_proxy``, ``https_proxy``, ``no_proxy``,
and ``all_proxy``.

.. admonition:: IPv6 in NO_PROXY
   :class: note

   Available since version 3.1.2

Uppercase variants of these variables are also supported.
You can therefore set them to configure Niquests (only set the ones relevant
to your needs)::

    $ export HTTP_PROXY="http://10.10.1.10:3128"
    $ export HTTPS_PROXY="http://10.10.1.10:1080"
    $ export ALL_PROXY="socks5://10.10.1.10:3434"

    $ python
    >>> import niquests
    >>> niquests.get('http://example.org')

To use HTTP Basic Auth with your proxy, use the `http://user:password@host/`
syntax in any of the above configuration entries::

    $ export HTTPS_PROXY="http://user:pass@10.10.1.10:1080"

    $ python
    >>> proxies = {'http': 'http://user:pass@10.10.1.10:3128/'}

.. warning:: Storing sensitive username and password information in an
   environment variable or a version-controlled file is a security risk and is
   highly discouraged.

To give a proxy for a specific scheme and host, use the
`scheme://hostname` form for the key.  This will match for
any request to the given scheme and exact hostname.

::

    proxies = {'http://10.20.1.128': 'http://10.10.1.10:5323'}

Note that proxy URLs must include the scheme.

Finally, note that using a proxy for https connections typically requires your
local machine to trust the proxy's root certificate. By default the list of
certificates trusted by Niquests can be found with::

    from wassima import generate_ca_bundle
    print(generate_ca_bundle())  # A concatenated PEM bundle as a string.

You override this default certificate bundle by setting the ``REQUESTS_CA_BUNDLE``
(or ``CURL_CA_BUNDLE``) environment variable to another file path::

    $ export REQUESTS_CA_BUNDLE="/usr/local/myproxy_info/cacert.pem"
    $ export https_proxy="http://10.10.1.10:1080"

    $ python
    >>> import niquests
    >>> niquests.get('https://example.org')

SOCKS
~~~~~

.. versionadded:: 2.10.0

In addition to basic HTTP proxies, Niquests also supports proxies using the
SOCKS protocol. This is an optional feature that requires that additional
third-party libraries be installed before use.

You can get the dependencies for this feature from ``pip``:

.. code-block:: bash

    $ python -m pip install niquests[socks]

Once you've installed those dependencies, using a SOCKS proxy is just as easy
as using an HTTP one::

    proxies = {
        'http': 'socks5://user:pass@host:port',
        'https': 'socks5://user:pass@host:port'
    }

Using the scheme ``socks5`` causes the DNS resolution to happen on the client, rather than on the proxy server. This is in line with curl, which uses the scheme to decide whether to do the DNS resolution on the client or proxy. If you want to resolve the domains on the proxy server, use ``socks5h`` as the scheme.

.. _compliance:

Compliance
----------

Niquests is intended to be compliant with all relevant specifications and
RFCs where that compliance will not cause difficulties for users. This
attention to the specification can lead to some behaviour that may seem
unusual to those not familiar with the relevant specification.

Encodings
~~~~~~~~~

When you receive a response, Niquests estimates the encoding to
use for decoding the response when you access the :attr:`Response.text
<niquests.Response.text>` attribute. Niquests will first check for an
encoding in the HTTP headers. If none is present, or if it is invalid, Niquests
uses `charset_normalizer <https://pypi.org/project/charset_normalizer/>`_
to attempt to guess the encoding.

If you require a different encoding, manually set
:attr:`Response.encoding <niquests.Response.encoding>`
property, or use the raw :attr:`Response.content <niquests.Response.content>`.

If Niquests cannot choose a suitable encoding, the :attr:`~niquests.Response.text` property on
:class:`~niquests.Response` returns ``None``. This has been the behavior since version
3 and avoids unsafe assumptions, including:

- Accidentally decoding a large binary payload.
- Treating an intentionally malformed payload as permissively decoded text.

.. _http-verbs:

HTTP verbs
----------

Niquests provides helpers for GET, OPTIONS, HEAD, POST, PUT, PATCH, DELETE, and
QUERY. Choosing among them is not merely a matter of syntax: each method communicates
different intent to servers, caches, and intermediaries.

The examples below use httpbingo's ``/anything`` endpoint. It echoes requests so that
we can inspect exactly what was sent without creating, changing, or deleting a real
resource.

Retrieving and inspecting a resource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GET retrieves a representation. Query parameters belong in ``params`` and are encoded
into the URL. Once the response arrives, inspect its status and representation rather
than assuming that the request succeeded.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        url = "https://httpbingo.org/anything"
        response = niquests.get(url, params={"page": 1})

        payload = response.json()
        assert response.status_code == 200
        assert payload["method"] == "GET"
        assert payload["args"] == {"page": ["1"]}

        head_response = niquests.head(url)
        assert head_response.status_code == 200
        assert head_response.content == b""

        options_response = niquests.options(url)
        assert options_response.status_code == 200

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        url = "https://httpbingo.org/anything"
        response = await niquests.aget(url, params={"page": 1})

        payload = response.json()
        assert response.status_code == 200
        assert payload["method"] == "GET"
        assert payload["args"] == {"page": ["1"]}

        head_response = await niquests.ahead(url)
        assert head_response.status_code == 200
        assert head_response.content == b""

        options_response = await niquests.aoptions(url)
        assert options_response.status_code == 200

HEAD asks for the same metadata as GET but omits the response body, making it useful
when headers are sufficient. OPTIONS asks about communication options for a resource.
A server may advertise supported methods in an ``Allow`` header, but many APIs provide
little or no OPTIONS metadata; consult the target API rather than assuming that header
will be present.

Submitting and modifying representations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

POST submits a representation, PUT conventionally replaces the state at a target URI,
PATCH describes a partial modification, and DELETE requests removal. Here httpbingo
only echoes each request. It lets us verify the method and JSON body without performing
those operations against a third-party API.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        url = "https://httpbingo.org/anything"

        response = niquests.post(url, json={"name": "draft"})
        assert response.json()["method"] == "POST"
        assert response.json()["json"] == {"name": "draft"}

        response = niquests.put(
            url,
            json={"name": "replacement", "enabled": True},
        )
        assert response.json()["method"] == "PUT"
        assert response.json()["json"] == {
            "name": "replacement",
            "enabled": True,
        }

        response = niquests.patch(url, json={"enabled": False})
        assert response.json()["method"] == "PATCH"
        assert response.json()["json"] == {"enabled": False}

        response = niquests.delete(url)
        assert response.json()["method"] == "DELETE"

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        url = "https://httpbingo.org/anything"

        response = await niquests.apost(url, json={"name": "draft"})
        assert response.json()["method"] == "POST"
        assert response.json()["json"] == {"name": "draft"}

        response = await niquests.aput(
            url,
            json={"name": "replacement", "enabled": True},
        )
        assert response.json()["method"] == "PUT"
        assert response.json()["json"] == {
            "name": "replacement",
            "enabled": True,
        }

        response = await niquests.apatch(url, json={"enabled": False})
        assert response.json()["method"] == "PATCH"
        assert response.json()["json"] == {"enabled": False}

        response = await niquests.adelete(url)
        assert response.json()["method"] == "DELETE"

The target API defines what a submitted representation means. In particular, POST does
not always create a resource, PUT is not necessarily accepted for every target, and a
PATCH document must use a format understood by the server.

Querying with a request body
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

QUERY is a safe, idempotent method for queries that are too large or structured to fit
comfortably in a URL. Unlike GET, it permits a request body while retaining retrieval
semantics. The server must explicitly support it.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        response = niquests.query(
            "https://httpbingo.org/anything",
            json={"status": "active", "limit": 10},
        )

        payload = response.json()
        assert payload["method"] == "QUERY"
        assert payload["json"] == {"status": "active", "limit": 10}

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        response = await niquests.aquery(
            "https://httpbingo.org/anything",
            json={"status": "active", "limit": 10},
        )

        payload = response.json()
        assert payload["method"] == "QUERY"
        assert payload["json"] == {"status": "active", "limit": 10}

HTTP classifies methods by whether they are *safe* (intended only to retrieve or inspect
state) and *idempotent* (repeating the same request has the same intended effect as
sending it once):

.. list-table:: HTTP method semantics
   :header-rows: 1
   :widths: 15 15 18 52

   * - Method
     - Safe
     - Idempotent
     - Typical purpose
   * - GET
     - Yes
     - Yes
     - Retrieve a representation
   * - HEAD
     - Yes
     - Yes
     - Retrieve response metadata
   * - OPTIONS
     - Yes
     - Yes
     - Discover communication options
   * - QUERY
     - Yes
     - Yes
     - Submit a structured retrieval query
   * - POST
     - No
     - No
     - Submit data for resource-specific processing
   * - PUT
     - No
     - Yes
     - Replace state at the target URI
   * - PATCH
     - No
     - No
     - Apply a partial modification
   * - DELETE
     - No
     - Yes
     - Request removal of a resource

These are protocol semantics, not guarantees that a server implements a method correctly
or accepts it for a particular resource. Always follow the target API's contract.

.. _custom-verbs:

Custom verbs
------------

From time to time you may be working with a server that, for whatever reason,
allows or requires HTTP methods not covered above. For example, some WebDAV servers
support MKCOL. Use the general request method.

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.request('MKCOL', url, data=data)

.. tab:: 🔀 Async

    .. code:: python

        response = await niquests.arequest('MKCOL', url, data=data)

This supports any method implemented by the target server.


.. _link-headers:

Link headers
------------

Many HTTP APIs feature Link headers. They make APIs more self-describing and
discoverable.

Niquests automatically parses these headers into :attr:`~niquests.Response.links`.

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.get('https://httpbingo.org/response-headers', params={
            'Link': '<https://example.test/page/2>; rel="next"'
        })
        print(response.links['next']['url'])

.. tab:: 🔀 Async

    .. code:: python

        response = await niquests.aget('https://httpbingo.org/response-headers', params={
            'Link': '<https://example.test/page/2>; rel="next"'
        })
        print(response.links['next']['url'])

.. _transport-adapters:

Transport adapters
------------------

As of v1.0.0, Niquests has moved to a modular internal design. Part of the
reason this was done was to implement Transport Adapters, originally
`described here`_. Transport Adapters provide a mechanism to define interaction
methods for an HTTP service. In particular, they allow you to apply per-service
configuration.

Niquests provides synchronous and asynchronous adapter families. A
:class:`HTTPAdapter <niquests.adapters.HTTPAdapter>` supplies the default HTTP and
HTTPS transport for :class:`Session <niquests.Session>`, while
:class:`~niquests.adapters.AsyncHTTPAdapter` provides the equivalent transport for
:class:`~niquests.AsyncSession`. Platform-specific transports may mount additional
adapters automatically.

Niquests enables users to create and use their own Transport Adapters that
provide specific functionality. Once created, a Transport Adapter can be
mounted to a session with a URL prefix.

.. tab:: 🔂 Sync

    .. code:: python

        session = niquests.Session()
        session.mount('https://example.com/', MyAdapter())

.. tab:: 🔀 Async

    .. code:: python

        session = niquests.AsyncSession()
        session.mount('https://example.com/', MyAsyncAdapter())

The mount call registers a specific instance of a Transport Adapter to a
prefix. Once mounted, any HTTP request made using that session whose URL starts
with the given prefix will use the given Transport Adapter.

.. note:: The adapter is selected by longest-prefix match. A prefix such as
   ``http://localhost`` also matches ``http://localhost.other.com`` and
   ``http://localhost@other.com``. End a complete hostname prefix with ``/``.

Many of the details of implementing a Transport Adapter are beyond the scope of
this document. Synchronous custom adapters subclass
:class:`BaseAdapter <niquests.adapters.BaseAdapter>`; asynchronous adapters subclass
:class:`~niquests.adapters.AsyncBaseAdapter`.

Example: specific TLS version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use :class:`~niquests.TLSConfiguration` rather than replacing an adapter merely to
constrain modern TLS versions::

    from niquests import Session, TLSConfiguration
    from niquests.packages.urllib3.contrib.anytls import ssl

    tls = TLSConfiguration(
        min_version=ssl.TLSVersion.TLSv1_2,
        max_version=ssl.TLSVersion.TLSv1_3,
    )
    session = Session(tls_configuration=tls)

Example: automatic retries
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Niquests does not retry failed connections. However, it is possible
to implement automatic retries with a powerful array of features, including
backoff, through :class:`~niquests.RetryConfiguration`::

    from niquests import RetryConfiguration, Session

    retries = RetryConfiguration(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={'GET'},
    )

    s = Session(retries=retries)
    s.get("https://1.1.1.1")

.. _`described here`: https://kenreitz.org/essays/2012/06/14/the-future-of-python-http
.. _`urllib3.future`: https://github.com/jawah/urllib3.future
.. _`urllib3.util.Retry`: https://urllib3-future.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry

.. _blocking-or-nonblocking:

Blocking or non-blocking?
-------------------------

For a synchronous response, accessing :attr:`Response.content <niquests.Response.content>`
blocks until the body has been downloaded. With ``multiplexed=True``, request submission
can return lazy responses without waiting for each server response, but resolving those
responses with :meth:`~niquests.Session.gather`, accessing a lazy attribute, or consuming
a body still blocks the calling thread. Multiplexing improves concurrency; it does not
turn synchronous code into non-blocking code.

Use :class:`~niquests.AsyncSession` when the event loop must remain available. Its
request methods and :meth:`~niquests.AsyncSession.gather` are awaitable, and streamed bodies use
:class:`~niquests.AsyncResponse`. Submit multiple multiplexed requests before gathering
or consuming them; premature access serializes work and loses much of the benefit.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session(multiplexed=True) as session:
            responses = [
                session.get("https://httpbingo.org/delay/2"),
                session.get("https://httpbingo.org/delay/1"),
            ]
            session.gather(*responses)
            for response in responses:
                print(response.status_code)

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession(multiplexed=True) as session:
            responses = [
                await session.get("https://httpbingo.org/delay/2"),
                await session.get("https://httpbingo.org/delay/1"),
            ]
            await session.gather(*responses)
            for response in responses:
                print(response.status_code)

Calling :meth:`~niquests.Session.gather` without response arguments resolves all pending responses.
:meth:`gather(*responses, max_fetch=n) <niquests.Session.gather>` limits each mounted adapter to resolving at most
``n`` responses during that call. Close the session only after pending responses have
been gathered or discarded; a context manager provides deterministic adapter and
resolver cleanup.

Header ordering
---------------

In unusual circumstances you may want to provide headers in an ordered manner. If you
pass an :class:`~collections.OrderedDict` to the ``headers`` keyword argument, that will
provide the headers with an ordering. *However*, the ordering of the default headers
used by Niquests will be preferred, which means that if you override default headers in
the ``headers`` keyword argument, they may appear out of order compared to other headers
in that keyword argument.

If this is problematic, users should consider setting the default headers on a
:class:`Session <niquests.Session>` object, by setting
:attr:`Session.headers <niquests.Session.headers>` to a custom
:class:`~collections.OrderedDict`. That ordering will always be preferred.

.. _timeouts:

Timeouts
--------

Niquests applies finite defaults. Top-level GET, HEAD, and OPTIONS calls default to 30
seconds; POST, PUT, PATCH, DELETE, QUERY, and the general top-level
:func:`~niquests.request` call
default to 120 seconds. Session request methods use 120 seconds for POST, PUT, PATCH,
DELETE, and QUERY, and 30 seconds for other methods, including custom methods, when
both their ``timeout`` argument and ``Session(timeout=...)`` value are ``None``.
Passing a timeout to the session constructor supplies a common default for all of its
requests.

The **connect** timeout is the number of seconds Niquests will wait for your
client to establish a connection to a remote machine (corresponding to the
`connect()`_) call on the socket. It's a good practice to set connect timeouts
to slightly larger than a multiple of 3, which is the default `TCP packet
retransmission window <https://www.hjp.at/doc/rfc/rfc2988.txt>`_.

Once your client has connected to the server and sent the HTTP request, the
**read** timeout is the number of seconds the client will wait for the server
to send a response. (Specifically, it's the number of seconds that the client
will wait *between* bytes sent from the server. In 99.9% of cases, this is the
time before the server sends the first byte).

If you specify a single value, it applies to both connect and read timeouts.

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.get('https://httpbingo.org/get', timeout=5)
        with niquests.Session(timeout=(3.05, 27)) as session:
            response = session.get('https://httpbingo.org/get')

.. tab:: 🔀 Async

    .. code:: python

        response = await niquests.aget('https://httpbingo.org/get', timeout=5)
        async with niquests.AsyncSession(timeout=(3.05, 27)) as session:
            response = await session.get('https://httpbingo.org/get')

Use :class:`~niquests.TimeoutConfiguration` for finer control::

    from niquests import TimeoutConfiguration

    response = niquests.get(
        'https://httpbingo.org/get',
        timeout=TimeoutConfiguration(connect=3, read=9),
    )

``timeout=None`` does not mean wait forever; it selects the method-specific default.
To disable connect and read deadlines explicitly, pass an appropriately configured
:class:`~niquests.TimeoutConfiguration`. Doing so is discouraged for external services.

.. _`connect()`: https://linux.die.net/man/2/connect

OCSP and certificate revocation
-------------------------------

A certificate can have a valid chain and validity period but still be revoked. When
``verify=True``, Niquests supplements normal TLS verification with Online Certificate
Status Protocol (OCSP) and certificate revocation list (CRL) checks where supported.
It prefers OCSP by default and can fall back to CRL. The default is soft-fail behavior,
similar to common browsers, because revocation responders can be unavailable.

Configure this per session with :class:`~niquests.RevocationConfiguration`, described
in `Revocation Configuration`_. This is the primary API for selecting OCSP/CRL order
and strict behavior. ``NIQUESTS_STRICT_OCSP`` remains an environment-wide compatibility
switch and also affects CRL checks, but explicit session configuration is clearer.

The :attr:`PreparedRequest.ocsp_verified <niquests.PreparedRequest.ocsp_verified>` and
:attr:`Response.ocsp_verified <niquests.Response.ocsp_verified>` properties report the
post-handshake result. Availability depends on
the installed revocation dependencies; run ``python -m niquests.help`` to inspect the
active stack. Niquests caches results in memory and may stop non-strict OCSP checks after
repeated responder failures to avoid degrading unrelated traffic.

Specify HTTP/3 capable endpoint preemptively
--------------------------------------------

Register an HTTP/3-capable host before the first TLS-over-TCP handshake.

.. tab:: 🔂 Sync

    .. code:: python

        session = niquests.Session()
        session.quic_cache_layer.add_domain("cloudflare.com")

.. tab:: 🔀 Async

    .. code:: python

        session = niquests.AsyncSession()
        session.quic_cache_layer.add_domain("cloudflare.com")

This will prevent the first request being made with HTTP/2 or HTTP/1.1.

.. note:: You can also specify an alternate destination port if QUIC is being served on anything else than 443.

Sample::

    s.quic_cache_layer.add_domain("cloudflare.com", alt_port=8544)

This would mean that attempting to request ``https://cloudflare.com/a/b`` will be routed through ``https://cloudflare.com:8544/a/b``
over QUIC.

.. warning:: You cannot specify another hostname for security reasons.

.. note:: Using a custom DNS resolver can solve the problem as we can probe the HTTPS record for the given hostname and connect directly using HTTP/3 over QUIC.

Prevent a domain from auto-upgrading to HTTP/3
----------------------------------------------

To prevent an Alt-Svc upgrade for one host:

.. tab:: 🔂 Sync

    .. code:: python

        session = niquests.Session()
        session.quic_cache_layer.exclude_domain("cloudflare.com")

.. tab:: 🔀 Async

    .. code:: python

        session = niquests.AsyncSession()
        session.quic_cache_layer.exclude_domain("cloudflare.com")

This will prevent the auto-upgrade to HTTP/3 via the Alt-Svc headers.

.. note:: This isolates a server that advertises unusable HTTP/3 support instead of
   disabling HTTP/3 for the entire session.

Increase the default Alt-Svc cache size
---------------------------------------

When a server advertises HTTP/3 over QUIC, the information is stored in a local,
thread-safe or task-safe in-memory cache.

That storage is limited to 12,288 entries by default, and you can override this
by passing a custom cache instance.

.. tab:: 🔂 Sync

    .. code:: python

        cache = niquests.structures.QuicSharedCache(max_size=128_000)
        session = niquests.Session(quic_cache_layer=cache)

.. tab:: 🔀 Async

    .. code:: python

        cache = niquests.structures.AsyncQuicSharedCache(max_size=128_000)
        session = niquests.AsyncSession(quic_cache_layer=cache)


.. note:: Passing ``None`` as the maximum size permits unbounded growth and can consume
   substantial memory.

When the cache is full, the oldest entry is removed.

Disable HTTP/1.1, HTTP/2, and/or HTTP/3
---------------------------------------

You can at your own discretion disable a protocol by passing ``disable_http2=True`` or
``disable_http3=True`` within your :class:`~niquests.Session` constructor.

Having a session without HTTP/2 enabled should be done that way::

    import niquests

    session = niquests.Session(disable_http2=True)


HTTP/2 with prior knowledge
---------------------------

Interacting with a server over plain text using the HTTP/2 protocol must be done by
disabling HTTP/1.1 entirely, so that Niquests knows that you know in advance what the remote is capable of.

Following this example::

    import niquests

    session = niquests.Session(disable_http1=True)
    r = session.get("http://my-special-svc.local")
    r.http_version  # 20 (HTTP/2)

.. note:: You may do the same for servers that do not support the ALPN extension for https URLs.

.. warning:: Disabling HTTP/1.1 and HTTP/2 raises :exc:`RuntimeError` for non-HTTPS URLs.
   HTTP/3 runs over QUIC and requires TLS 1.3.

Thread safety
-------------

Niquests sessions are designed to be thread-safe and task-safe. Report correctness or
lock-contention problems through the project's GitHub issue tracker.

Use a custom CA without losing the system CAs
---------------------------------------------

There's an interesting use-case where a user may want to be able to request both private
and public HTTP endpoints without doing some gymnastic with ``verify=...``.

Thanks to our underlying library ``wassima`` you can register globally your own set
of certificate authorities like so::

    import wassima

    wassima.register_ca(my_own_ca_pem_str)

That's it! Niquests will now automatically recognize it and use it to verify your secure endpoints.
You'll have to register it prior to your HTTP requests.

.. warning:: Reusable library maintainers must not call ``wassima.register_ca`` on
   behalf of their users. Registration expands the process-wide default trust policy
   for subsequent TLS contexts, and the added CA can authenticate any hostname for
   which it issues a certificate, not only the library's own service. Trust decisions
   belong to the application: expose an opt-in CA setting and let the application pass
   it through ``verify`` or register it explicitly. Never register a CA at import time.

.. note:: While doing local development with HTTPS, we recommend using tool like ``mkcert`` that will register the CA into your local machine trust store. Niquests is natively capable of picking them up.

Disable either IPv4 or IPv6
---------------------------

You may be interested in controlling what kind of address you would accept connecting to.
Since Niquests 3.4+, you can configure that aspect per :class:`~niquests.Session` instance.

Having a session without IPv6 enabled should be done that way::

    import niquests

    session = niquests.Session(disable_ipv6=True)

.. warning:: Setting both ``disable_ipv4`` and ``disable_ipv6`` raises :exc:`RuntimeError`.

Setting the source network adapter
----------------------------------

Bind outgoing connections to a local address and port with ``source_address``::

    import niquests

    session = niquests.Session(source_address=("10.10.4.1", 4444))

Use port ``0`` to select an ephemeral port. Use ``0.0.0.0`` as the address to let the
system select an IPv4 interface while fixing only the local port.

Inspect network timings
-----------------------

:attr:`response.elapsed <niquests.Response.elapsed>` measures the time until the response
is established; it does not include subsequent streamed-body consumption.
:attr:`response.conn_info <niquests.Response.conn_info>` exposes individual
DNS, connection, TLS, and transmission timings.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session() as session:
            response = session.get("https://httpbingo.org/get")
            print(response.conn_info.resolution_latency)
            print(response.conn_info.tls_handshake_latency)

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as session:
            response = await session.get("https://httpbingo.org/get")
            print(response.conn_info.resolution_latency)
            print(response.conn_info.tls_handshake_latency)

Here, :attr:`~niquests.Response.conn_info` is a
:class:`urllib3.ConnectionInfo <urllib3.backend._base.ConnectionInfo>` instance. The complete list of
attributes is listed on the Hook bottom section.

.. note:: Each response and request are linked to a unique ConnectionInfo.

Verify certificate fingerprint
------------------------------

.. versionadded:: 3.5.4

Certificate fingerprint pinning is an alternative verification policy. Pin rotation is
operationally fragile, so prefer normal CA and hostname verification.

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.get(url, verify=f"sha256_{expected_sha256}")

.. tab:: 🔀 Async

    .. code:: python

        response = await niquests.aget(url, verify=f"sha256_{expected_sha256}")

.. warning:: SHA-256 and SHA-1 are supported, and the ``sha256_`` or ``sha1_`` prefix
   is mandatory.

TLS fingerprints such as JA3 and JA4
------------------------------------

.. versionadded:: 3.19.0

Niquests supports swappable TLS backends. The optional ``utls`` backend uses BoringSSL
and can present a browser-like TLS fingerprint.

Install the optional backend with::

    pip install niquests[utls]

To know which backend is effective, run::

    python -m niquests.help

The diagnostic output identifies BoringSSL when it is active.

.. warning:: A TLS fingerprint does not bypass authorization, rate limits, access
   policies, or IP-based blocking. Respect the service's terms and limits.

.. versionadded:: 3.20.0

Select it explicitly with ``tls_configuration``.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session(
            tls_configuration=niquests.TLSConfiguration(backend="utls")
        ) as session:
            response = session.get(url)

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession(
            tls_configuration=niquests.TLSConfiguration(backend="utls")
        ) as session:
            response = await session.get(url)

Tracking raw download progress
--------------------------------

Niquests automatically decompresses response bodies. Consequently, chunk lengths from
:meth:`~niquests.Response.iter_content` represent decoded bytes rather than bytes read
from the socket. With ``stream=True``,
:attr:`~niquests.Response.download_progress` may expose a
:class:`~niquests.models.TransferProgress` instance that
tracks raw transport bytes when the transport provides byte counters and the response
has a valid ``Content-Length`` header.

.. note:: :attr:`~niquests.Response.download_progress` remains ``None`` when the transport cannot expose raw
   byte counts or the response length is unknown.

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session() as session:
            with session.get(url, stream=True) as response:
                for chunk in response.iter_content():
                    process(chunk)
                    if response.download_progress is not None:
                        print(response.download_progress.total)

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as session:
            async with await session.get(url, stream=True) as response:
                async for chunk in await response.iter_content():
                    process(chunk)
                    if response.download_progress is not None:
                        print(response.download_progress.total)


HTTP trailers
-------------

.. versionadded:: 3.8

An HTTP response may contain trailer fields received after its body.

Quoted from Mozilla MDN: "The Trailer response header allows the sender to include additional fields
at the end of chunked messages in order to supply metadata that might be dynamically generated while the
message body is sent, such as a message integrity check, digital signature, or post-processing status."

.. tab:: 🔂 Sync

    .. code:: python

        response = niquests.get('https://httpbingo.org/trailers?foo=baz')
        print(response.trailers)  # {'foo': 'baz'}

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession() as session:
            response = await session.get(
                'https://httpbingo.org/trailers?foo=baz', stream=True
            )
            await response.content
            print(response.trailers)  # {'foo': 'baz'}


.. warning:: :attr:`~niquests.Response.trailers` is populated only after the body has
   been consumed completely. Before then, it is an empty
   :class:`~niquests.structures.CaseInsensitiveDict`.

Early responses
---------------

A server may send one or more informational responses before its final response. A
common example is `103 Early Hints
<https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/103>`_. Observe them with the
``early_response`` hook.

.. tab:: 🔂 Sync

    .. code:: python

        def early_response_hook(response, **kwargs):
            print(response.status_code, response.headers)

        with niquests.Session() as session:
            response = session.get(
                "https://early-hints.fastlylabs.com/",
                hooks={"early_response": [early_response_hook]},
            )

.. tab:: 🔀 Async

    .. code:: python

        async def early_response_hook(response, **kwargs):
            print(response.status_code, response.headers)

        async with niquests.AsyncSession() as session:
            response = await session.get(
                "https://early-hints.fastlylabs.com/",
                hooks={"early_response": [early_response_hook]},
            )

Niquests supports informational responses over HTTP/1.1, HTTP/2, and HTTP/3, although
individual servers may expose them only on selected protocols.

.. _wasi-advanced:

WASI transports and capabilities
--------------------------------

.. versionadded:: 3.21.0

WASI separates a component's *static contract* from the host's *runtime grant*.
Importing a socket or HTTP interface in a WIT world makes that operation representable;
it does not grant ambient authority. Conversely, a host network flag cannot help a
component whose world omitted the corresponding interface. A successful deployment
needs both halves.

Niquests performs capability discovery from the generated ``wit_world`` bindings and
selects a transport without exposing WASI-specific application APIs:

- A synchronous :class:`~niquests.Session` prefers Preview 2 sockets. Preview 1
  socket compatibility remains available as a legacy heuristic, but should not be
  selected for new components.
- An asynchronous :class:`~niquests.AsyncSession` prefers Preview 3 sockets.
- If matching sockets are absent, synchronous code can use ``wasi:http@0.2.0`` and
  asynchronous code can use ``wasi:http@0.3.0``.
- When sockets are present without a usable Rustls backend, Niquests can use sockets
  for plaintext HTTP and the matching WIT HTTP interface for HTTPS. This hybrid
  arrangement lets the host retain TLS authority.

Native socket support requires urllib3.future 2.24.900 or newer. HTTPS over those
sockets additionally requires ``niquests[rtls]``. If neither a usable socket contract
nor a matching WIT HTTP contract is present, requests fail with
:exc:`~niquests.exceptions.InvalidSchema` rather than silently escaping the sandbox.

Socket WIT
~~~~~~~~~~

For componentize-py applications, these command worlds are the recommended starting
point:

.. code:: text

    package example:client;

    world sync-client {
        include wasi:cli/command@0.2.0;
    }

    world async-client {
        include wasi:cli/command@0.3.0;
    }

The command worlds provide the matching socket, polling, clock, random, CLI, and
filesystem interfaces expected by the Python runtime and urllib3.future. Interface
presence is not equivalent to host filesystem access: files remain inaccessible until
a directory is explicitly preopened.

With Wasmtime, a typical socket grant is:

.. code:: console

    $ wasmtime run -Sinherit-network -Sallow-ip-name-lookup=y component.wasm

Add ``-Sp3`` for a Preview 3 component. ``inherit-network`` is broad authority: it
allows the guest to use the host network namespace. Prefer runtime-specific address,
port, and DNS allowlists where available. ``allow-ip-name-lookup`` permits host name
resolution; omitting it is useful for components restricted to literal addresses, but
normal HTTPS URLs will generally require it.

The socket path preserves the native urllib3.future transport model. Its practical
properties include:

- DNS and connection establishment occur through WASI sockets.
- Sessions pool and reuse connections and can multiplex HTTP/2 streams.
- HTTP version controls, source addresses, custom resolvers, proxies, WebSockets, SSE,
  response trailers, and connection metadata remain available when their own
  dependencies and permissions are present.
- TLS executes inside the component through Rustls. Certificate bundles, client
  certificates, and verification policy therefore belong to the guest rather than
  the host HTTP service.
- Pool sizing and keep-alive settings consume component resources and can increase the
  number of simultaneously open host sockets.

WIT HTTP
~~~~~~~~

WIT HTTP is a higher-level capability. Instead of receiving TCP sockets, the component
submits an HTTP request resource to the host. A minimal HTTP-oriented world adds the
following imports to the CLI, clock, random, filesystem, and I/O interfaces required by
the Python runtime:

.. code:: text

    // Synchronous Preview 2
    import wasi:http/types@0.2.0;
    import wasi:http/outgoing-handler@0.2.0;

    // Asynchronous Preview 3
    import wasi:http/types@0.3.0;
    import wasi:http/client@0.3.0;

The corresponding Wasmtime grant is ``-Shttp``; Preview 3 additionally needs
``-Sp3``. No inherited socket permission is required. This is a smaller and often more
appropriate authority surface for untrusted plug-ins and edge functions that only
need outbound HTTP. ``-Sallow-ip-name-lookup=y`` is also unnecessary on this path:
the component passes an authority to the host HTTP service, which performs DNS under
the host's own policy.

The reduction in authority intentionally moves transport policy to the host:

- The host owns DNS, TCP, TLS, certificate trust, and protocol negotiation.
  ``verify=False``, custom CA bundles, and TLS client certificates are consequently
  rejected.
- Custom DNS resolvers, source-address binding, SOCKS/HTTP proxies, and raw WebSocket
  upgrades are unavailable because the component never receives a socket.
- The negotiated HTTP version and low-level connection information are not exposed by
  the WIT contract. :attr:`response.http_version <niquests.Response.http_version>` and
  :attr:`response.conn_info <niquests.Response.conn_info>` should not be
  used for transport decisions on this path.
- Connection reuse, multiplexing, and maximum concurrency are host concerns. Pool
  sizing and HTTP-version toggles cannot compel the host to change its behavior.
- WASI HTTP has no intermediate-response channel, so the ``early_response`` hook does
  not observe informational 1xx responses.
- Request and response body streaming, SSE, retries, cookies, redirects, upload
  progress, trailers, and ``allow_redirects=False`` remain managed by Niquests where
  the WIT version exposes the necessary resources.
- Connect, first-byte, and between-byte timeout values are passed to WIT request
  options. Enforcement and error timing ultimately belong to the host implementation.

Host behavior is implementation-specific. For example, Wasmtime's stock WASI HTTP
service currently uses HTTP/1.1 and may establish a fresh DNS/TCP/TLS path per request;
another host may pool or route requests differently. Code using WIT HTTP should treat
those details as opaque.

Permission design
~~~~~~~~~~~~~~~~~

Use the narrowest contract that still provides the semantics your application needs:

.. list-table::
   :header-rows: 1
   :widths: 22 24 25 29

   * - Requirement
     - WIT contract
     - Typical Wasmtime grant
     - Security and behavior impact
   * - Outbound HTTP only
     - ``wasi:http`` 0.2 or 0.3
     - ``-Shttp``
     - Host mediates DNS, TLS, protocols, and destinations.
   * - Native synchronous networking
     - Preview 2 sockets
     - ``-Sinherit-network -Sallow-ip-name-lookup=y``
     - Guest controls pooling and transport; receives broad socket authority.
   * - Native asynchronous networking
     - Preview 3 sockets
     - ``-Sp3 -Sinherit-network -Sallow-ip-name-lookup=y``
     - Same transport control with the evolving P3 async ABI.
   * - Host files
     - Filesystem interfaces plus preopens
     - ``--dir host::/guest``
     - Exposes the selected host subtree; unrelated to basic network access.
   * - HTTPS over sockets
     - P2/P3 sockets plus Rustls
     - ``-Sinherit-network -Sallow-ip-name-lookup=y``
     - TLS keys, trust, and verification execute inside the guest.
   * - HTTPS through the host
     - Matching WIT HTTP
     - ``-Shttp``
     - Host trust policy is mandatory; guest TLS customization is unavailable.

Avoid importing both transports merely as a precaution. Socket capability takes
precedence, so adding socket WIT and broad network grants changes both the authority
surface and the selected implementation. Include both only for a deliberate hybrid or
portable world, and test each host policy independently.


Pyodide and browser constraints
-------------------------------

The :doc:`quickstart <quickstart>` section "Running in the Browser (Pyodide)" contains
setup and WebSocket/SSE examples. Advanced transport configuration has different
semantics in a browser because the browser owns networking:

- CORS, forbidden-header rules, browser credential policy, and mixed-content policy apply.
- Custom resolvers, proxies, source-address binding, certificate verification and
  client certificates, revocation checks, ECH, TLS backends, and TLS fingerprints are
  unavailable or ignored.
- Pool sizing, HTTP version toggles, Happy Eyeballs, keep-alive tuning, and Niquests
  multiplexing cannot control the browser's connection pool.
- :attr:`response.http_version <niquests.Response.http_version>` and
  :attr:`response.conn_info <niquests.Response.conn_info>` are unavailable, redirect
  history is constrained, and ``pre_send`` and ``early_response`` hooks cannot observe
  browser-internal transport events.
- Synchronous APIs require a JSPI-capable browser or Node.js runtime. Prefer async APIs.
- Browser WebSockets and SSE use native browser facilities rather than socket transports.

These are browser-sandbox constraints, not permissions that Niquests can bypass. Keep
transport-sensitive code behind platform checks and test it in the target browser.


Revocation configuration
------------------------

.. versionadded:: 3.16.0

Use ``revocation_configuration`` to select revocation behavior per session.

.. tab:: 🔂 Sync

    .. code-block:: python

        from niquests import RevocationConfiguration, RevocationStrategy, Session

        configuration = RevocationConfiguration(
            strategy=RevocationStrategy.PREFER_CRL,
            strict_mode=True,
        )
        with Session(revocation_configuration=configuration) as session:
            response = session.get("https://one.one.one.one")

.. tab:: 🔀 Async

    .. code-block:: python

        from niquests import AsyncSession, RevocationConfiguration, RevocationStrategy

        configuration = RevocationConfiguration(
            strategy=RevocationStrategy.PREFER_CRL,
            strict_mode=True,
        )
        async with AsyncSession(revocation_configuration=configuration) as session:
            response = await session.get("https://one.one.one.one")

.. warning:: Passing ``revocation_configuration=None`` disables revocation checks.
   This removes a security layer and should be limited to environments with an explicit
   alternative revocation policy.

You have three revocation strategies:

- ``RevocationStrategy.PREFER_OCSP``
- ``RevocationStrategy.PREFER_CRL``
- ``RevocationStrategy.CHECK_ALL``

.. note:: ``PREFER_`` attempts the named mechanism first and falls back to the other
   when necessary; it does not disable the fallback.

.. warning:: ``CHECK_ALL`` can significantly slow new connections. Use it only when
   required by the application's security policy.

By default, Niquests uses ``PREFER_OCSP``, but we may change that in a future version.


Inspecting pooling state or connections
---------------------------------------

.. versionadded:: 3.16.0

Session representations summarize adapters and current pool state, which can help answer
questions such as:

- How many connections are open?
- Has the session connected to a particular host?
- Are all current pools using HTTPS?

.. tab:: 🔂 Sync

    .. code-block:: python

        with niquests.Session() as session:
            response = session.get("https://one.one.one.one")
            print(session)

.. tab:: 🔀 Async

    .. code-block:: python

        async with niquests.AsyncSession() as session:
            response = await session.get("https://one.one.one.one")
            print(session)

.. warning:: Building this representation inspects pool internals and can be expensive.
   Do not call it on a hot path.

Alternative TLS backend
-----------------------

.. versionadded:: 3.18.3

Python is often built against OpenSSL or LibreSSL (depending on your OS), leaving no real alternative, at least easily.
Niquests is capable to use Rustls (via AWS-LC) with a mere extra::

    pip install niquests[rtls]

.. note:: Running ``python -m niquests.help`` should print Rustls instead of OpenSSL.

The ``rtls`` package is a drop-in replacement for the :mod:`ssl` stdlib. It is built against Rustls, that itself is built
against aws-lc-rs.

It's a memory-safe TLS backend. To learn more about it, visit https://github.com/jawah/rtls
Any issue encountered with it should be reported directly to the linked repository.

.. versionadded:: 3.20.0

Select the backend explicitly.

.. tab:: 🔂 Sync

    .. code:: python

        session = niquests.Session(
            tls_configuration=niquests.TLSConfiguration(backend="rtls")
        )

.. tab:: 🔀 Async

    .. code:: python

        session = niquests.AsyncSession(
            tls_configuration=niquests.TLSConfiguration(backend="rtls")
        )

.. note:: This is useful when the user may have multiple TLS backends installed in the environment.

Encrypted Client Hello
----------------------

.. versionadded:: 3.18.3

Encrypted Client Hello (ECH) requires HTTPS DNS records containing the server's ECH
configuration.

.. tab:: 🔂 Sync

    .. code-block:: python

        import niquests

        with niquests.Session(resolver="doh+cloudflare://") as session:
            response = session.get("https://encryptedsni.com", allow_redirects=False)
            accepted = bool(
                response.conn_info
                and getattr(response.conn_info, "tls_ech_accepted", False)
            )
            print("ECH was accepted." if accepted else "ECH was not accepted.")

.. tab:: 🔀 Async

    .. code-block:: python

        import niquests

        async with niquests.AsyncSession(resolver="doh+cloudflare://") as session:
            response = await session.get(
                "https://encryptedsni.com", allow_redirects=False
            )
            accepted = bool(
                response.conn_info
                and getattr(response.conn_info, "tls_ech_accepted", False)
            )
            print("ECH was accepted." if accepted else "ECH was not accepted.")

.. warning:: A custom resolver capable of HTTPS-record queries is required because the
   standard-library system resolver does not expose those records. Without a trusted
   HTTPS record, Niquests cannot obtain the HPKE public key used by ECH.

.. note:: This example requires urllib3.future 2.19.900 or later and a TLS backend with
   ECH support. Depending on the environment, install the ``rtls`` extra.

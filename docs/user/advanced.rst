.. _advanced:

Advanced Usage
==============

This document covers some of Niquests more advanced features.

.. _session-objects:

Session Objects
---------------

The Session object allows you to persist certain parameters across
niquests. It also persists cookies across all requests made from the
Session instance, and will use ``urllib3.future``'s `connection pooling`_. So if
you're making several requests to the same host, the underlying TCP
connection will be reused, which can result in a significant performance
increase (see `HTTP persistent connection`_).

A Session object has all the methods of the main Niquests API.

Let's persist some cookies across requests::

    s = niquests.Session()

    s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
    r = s.get('https://httpbin.org/cookies')

    print(r.text)
    # '{"cookies": {"sessioncookie": "123456789"}}'


Sessions can also be used to provide default data to the request methods. This
is done by providing data to the properties on a Session object::

    s = niquests.Session()
    s.auth = ('user', 'pass')
    s.headers.update({'x-test': 'true'})

    # both 'x-test' and 'x-test2' are sent
    s.get('https://httpbin.org/headers', headers={'x-test2': 'true'})


Any dictionaries that you pass to a request method will be merged with the
session-level values that are set. The method-level parameters override session
parameters.

Note, however, that method-level parameters will *not* be persisted across
requests, even if using a session. This example will only send the cookies
with the first request, but not the second::

    s = niquests.Session()

    r = s.get('https://httpbin.org/cookies', cookies={'from-my': 'browser'})
    print(r.text)
    # '{"cookies": {"from-my": "browser"}}'

    r = s.get('https://httpbin.org/cookies')
    print(r.text)
    # '{"cookies": {}}'


If you want to manually add cookies to your session, use the
:ref:`Cookie utility functions <api-cookies>` to manipulate
:attr:`Session.cookies <niquests.Session.cookies>`.

Sessions can also be used as context managers::

    with niquests.Session() as s:
        s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')

This will make sure the session is closed as soon as the ``with`` block is
exited, even if unhandled exceptions occurred.


.. admonition:: Remove a Value From a Dict Parameter

    Sometimes you'll want to omit session-level keys from a dict parameter. To
    do this, you simply set that key's value to ``None`` in the method-level
    parameter. It will automatically be omitted.

All values that are contained within a session are directly available to you.
See the :ref:`Session API Docs <sessionapi>` to learn more.

The ``Session`` class takes two (optional) named arguments for your convenience.

- `quic_cache_layer`
  Specify a `MutableMapping` that can memorize Alt-Svc capabilities (when a server is HTTP/3 compatible).

- `retries`
  Determine the retry strategy across the ``Session`` lifetime.

.. _request-and-response-objects:

Request and Response Objects
----------------------------

Whenever a call is made to ``niquests.get()`` and friends, you are doing two
major things. First, you are constructing a ``Request`` object which will be
sent off to a server to request or query some resource. Second, a ``Response``
object is generated once Niquests gets a response back from the server.
The ``Response`` object contains all of the information returned by the server and
also contains the ``Request`` object you created originally. Here is a simple
request to get some very important information from Wikipedia's servers::

    >>> r = niquests.get('https://en.wikipedia.org/wiki/Monty_Python')

If we want to access the headers the server sent back to us, we do this::

    >>> r.headers
    {'content-length': '56170', 'x-content-type-options': 'nosniff', 'x-cache':
    'HIT from cp1006.eqiad.wmnet, MISS from cp1010.eqiad.wmnet', 'content-encoding':
    'gzip', 'age': '3080', 'content-language': 'en', 'vary': 'Accept-Encoding,Cookie',
    'server': 'Apache', 'last-modified': 'Wed, 13 Jun 2012 01:33:50 GMT',
    'connection': 'close', 'cache-control': 'private, s-maxage=0, max-age=0,
    must-revalidate', 'date': 'Thu, 14 Jun 2012 12:59:39 GMT', 'content-type':
    'text/html; charset=UTF-8', 'x-cache-lookup': 'HIT from cp1006.eqiad.wmnet:3128,
    MISS from cp1010.eqiad.wmnet:80'}

However, if we want to get the headers we sent the server, we simply access the
request, and then the request's headers::

    >>> r.request.headers
    {'Accept-Encoding': 'identity, deflate, compress, gzip',
    'Accept': '*/*', 'User-Agent': 'python-requests/1.2.0'}

.. _prepared-requests:

Prepared Requests
-----------------

Whenever you receive a :class:`Response <niquests.Response>` object
from an API call or a Session call, the ``request`` attribute is actually the
``PreparedRequest`` that was used. In some cases you may wish to do some extra
work to the body or headers (or anything else really) before sending a
request. The simple recipe for this is the following::

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

Since you are not doing anything special with the ``Request`` object, you
prepare it immediately and modify the ``PreparedRequest`` object. You then
send that with the other parameters you would have sent to ``niquests.*`` or
``Session.*``.

However, the above code will lose some of the advantages of having a Requests
:class:`Session <niquests.Session>` object. In particular,
:class:`Session <niquests.Session>`-level state such as cookies will
not get applied to your request. To get a
:class:`PreparedRequest <niquests.PreparedRequest>` with that state
applied, replace the call to :meth:`Request.prepare()
<niquests.Request.prepare>` with a call to
:meth:`Session.prepare_request() <niquests.Session.prepare_request>`, like this::

    from niquests import Request, Session

    s = Session()
    req = Request('GET',  url, data=data, headers=headers)

    prepped = s.prepare_request(req)

    # do something with prepped.body
    prepped.body = 'Seriously, send exactly these bytes.'

    # do something with prepped.headers
    prepped.headers['Keep-Dead'] = 'parrot'

    resp = s.send(prepped,
        stream=stream,
        verify=verify,
        proxies=proxies,
        cert=cert,
        timeout=timeout
    )

    print(resp.status_code)

When you are using the prepared request flow, keep in mind that it does not take into account the environment.
This can cause problems if you are using environment variables to change the behaviour of niquests.
For example: Self-signed SSL certificates specified in ``REQUESTS_CA_BUNDLE`` will not be taken into account.
As a result an ``SSL: CERTIFICATE_VERIFY_FAILED`` is thrown.
You can get around this behaviour by explicitly merging the environment settings into your session::

    from niquests import Request, Session

    s = Session()
    req = Request('GET', url)

    prepped = s.prepare_request(req)

    # Merge environment settings into session
    settings = s.merge_environment_settings(prepped.url, {}, None, None, None)
    resp = s.send(prepped, **settings)

    print(resp.status_code)

.. _verification:

SSL Cert Verification
---------------------

Niquests verifies SSL certificates for HTTPS requests, just like a web browser.
By default, SSL verification is enabled, and Niquests will throw a SSLError if
it's unable to verify the certificate::

    >>> niquests.get('https://requestb.in')
    niquests.exceptions.SSLError: hostname 'requestb.in' doesn't match either of '*.herokuapp.com', 'herokuapp.com'

I don't have SSL setup on this domain, so it throws an exception. Excellent. GitHub does though::

    >>> niquests.get('https://github.com')
    <Response HTTP/2 [200]>

You can pass ``verify`` the path to a CA_BUNDLE file or directory with certificates of trusted CAs::

    >>> niquests.get('https://github.com', verify='/path/to/certfile')

or persistent::

    s = niquests.Session()
    s.verify = '/path/to/certfile'

.. note:: If ``verify`` is set to a path to a directory, the directory must have been processed using
  the ``c_rehash`` utility supplied with OpenSSL.

This list of trusted CAs can also be specified through the ``REQUESTS_CA_BUNDLE`` environment variable.
If ``REQUESTS_CA_BUNDLE`` is not set, ``CURL_CA_BUNDLE`` will be used as fallback.

Niquests can also ignore verifying the SSL certificate if you set ``verify`` to False::

    >>> niquests.get('https://kennethreitz.org', verify=False)
    <Response HTTP/2 [200]>

Note that when ``verify`` is set to ``False``, requests will accept any TLS
certificate presented by the server, and will ignore hostname mismatches
and/or expired certificates, which will make your application vulnerable to
man-in-the-middle (MitM) attacks. Setting verify to ``False`` may be useful
during local development or testing.

By default, ``verify`` is set to True. Option ``verify`` only applies to host certs.

Client Side Certificates
------------------------

You can also specify a local cert to use as client side certificate, as a single
file (containing the private key and the certificate) or as a tuple of both
files' paths::

    >>> niquests.get('https://kennethreitz.org', cert=('/path/client.cert', '/path/client.key'))
    <Response HTTP/2 [200]>

or persistent::

    s = niquests.Session()
    s.cert = '/path/client.cert'

If you specify a wrong path or an invalid cert, you'll get a SSLError::

    >>> niquests.get('https://kennethreitz.org', cert='/wrong_path/client.pem')
    SSLError: [Errno 336265225] _ssl.c:347: error:140B0009:SSL routines:SSL_CTX_use_PrivateKey_file:PEM lib

.. warning:: The private key to your local certificate *must* be unencrypted in above example.

You may specify the private key passphrase using the following example::

    >>> niquests.get('https://kennethreitz.org', cert=('/path/client.cert', '/path/client.key', 'my_key_password'))
    <Response HTTP/2 [200]>

DNS with mTLS
~~~~~~~~~~~~~

You can pass your client side certificate to authenticate yourself against the given resolver.
To do so, you will have to do as follow::

    from urllib3 import ResolverDescription
    from niquests import Session

    rd = ResolverDescription.from_url("doq://my-resolver.tld")
    rd["cert_data"] = in_memory_cert  # not a path, it should contain your cert content PEM format directly
    rd["cert_key"] = ...
    rd["key_password"] = ...

    with Session(resolver=rd) as s:
        ...

.. note:: Instead of in-memory cert, you can pass file path instead with ``cert_file``, ``key_file``.

This method of authentication is broadly used with DNS over TLS, QUIC, and HTTPS.

In-memory Certificates
----------------------

The ``cert=...`` and ``verify=...`` can actually take the certificates themselves. Niquests support
in-memory certificates instead of file paths.

.. _ca-certificates:

CA Certificates
---------------

Niquests uses certificates provided by the package `wassima`_. This allows for users
to not care about root CAs. By default it is expected to use your operating system root CAs.
You have nothing to do.

.. _HTTP persistent connection: https://en.wikipedia.org/wiki/HTTP_persistent_connection
.. _connection pooling: https://urllib3.readthedocs.io/en/latest/reference/index.html#module-urllib3.connectionpool
.. _wassima: https://github.com/jawah/wassima
.. _body-content-workflow:

Body Content Workflow
---------------------

By default, when you make a request, the body of the response is downloaded
immediately. You can override this behaviour and defer downloading the response
body until you access the :attr:`Response.content <niquests.Response.content>`
attribute with the ``stream`` parameter::

    tarball_url = 'https://github.com/jawah/niquests/tarball/main'
    r = niquests.get(tarball_url, stream=True)

At this point only the response headers have been downloaded and the connection
remains open, hence allowing us to make content retrieval conditional::

    if int(r.headers['content-length']) < TOO_LONG:
      content = r.content
      ...

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
make the request within a ``with`` statement to ensure it's always closed::

    with niquests.get('https://httpbin.org/get', stream=True) as r:
        # Do things with the response here.

.. _keep-alive:

Keep-Alive
----------

Excellent news — thanks to urllib3.future, keep-alive is 100% automatic within a session!
Any requests that you make within a session will automatically reuse the appropriate
connection!

Note that connections are only released back to the pool for reuse once all body
data has been read; be sure to either set ``stream`` to ``False`` or read the
``content`` property of the ``Response`` object.

.. _streaming-uploads:

Streaming Uploads
-----------------

Niquests supports streaming uploads, which allow you to send large streams or
files without reading them into memory. To stream and upload, simply provide a
file-like object for your body::

    with open('massive-body', 'rb') as f:
        niquests.post('http://some.url/streamed', data=f)

.. warning:: It is recommended that you open files in binary mode.


.. _chunk-encoding:

Chunk-Encoded Requests
----------------------

Niquests also supports Chunked transfer encoding for outgoing and incoming niquests.
To send a chunk-encoded request, simply provide a generator (or any iterator without
a length) for your body::

    def gen():
        yield 'hi'
        yield 'there'

    niquests.post('http://some.url/chunked', data=gen())

For chunked encoded responses, it's best to iterate over the data using
:meth:`Response.iter_content() <niquests.Response.iter_content>`. In
an ideal situation you'll have set ``stream=True`` on the request, in which
case you can iterate chunk-by-chunk by calling ``iter_content`` with a ``chunk_size``
parameter of ``None``. If you want to set a maximum size of the chunk,
you can set a ``chunk_size`` parameter to any integer.

.. note:: Since Niquests v3.7.1+ we support having async iterable passed down to ``data=...`` via your ``AsyncSession``.

.. _multipart:

POST Multiple Multipart-Encoded Files
-------------------------------------

You can send multiple files in one request. For example, suppose you want to
upload image files to an HTML form with a multiple file field 'images'::

    <input type="file" name="images" multiple="true" required="true"/>

To do that, just set files to a list of tuples of ``(form_field_name, file_info)``::

    >>> url = 'https://httpbin.org/post'
    >>> multiple_files = [
    ...     ('images', ('foo.png', open('foo.png', 'rb'), 'image/png')),
    ...     ('images', ('bar.png', open('bar.png', 'rb'), 'image/png'))]
    >>> r = niquests.post(url, files=multiple_files)
    >>> r.text
    {
      ...
      'files': {'images': 'data:image/png;base64,iVBORw ....'}
      'Content-Type': 'multipart/form-data; boundary=3131623adb2043caaeb5538cc7aa0b3a',
      ...
    }

.. warning:: It is recommended that you open files in binary
             mode. Errors may occur if you open the file in *text mode*.
             This because it is going to be re-encoded later in the process.


.. _event-hooks:

Event Hooks
-----------

Niquests has a hook system that you can use to manipulate portions of
the request process, or signal event handling.

Available hooks:

``response``:
    The response generated from a Request.
``pre_send``:
    The prepared request got his ConnectionInfo injected. This event is triggered just after picking a live connection from the pool.
``on_upload``:
    Permit to monitor the upload progress of passed body. This event is triggered each time a block of data is transmitted to the remote peer.
    Use this hook carefully as it may impact the overall performance.
``pre_request``:
    The prepared request just got built. You may alter it prior to be sent through HTTP.

You can assign a hook function on a per-request basis by passing a
``{hook_name: callback_function}`` dictionary to the ``hooks`` request
parameter::

    hooks={'response': print_url}

That ``callback_function`` will receive a chunk of data as its first
argument.

::

    def print_url(r, *args, **kwargs):
        print(r.url)

Your callback function must handle its own exceptions. Any unhandled exception won't be passed silently and thus should be handled by the code calling Niquests.

If the callback function returns a value, it is assumed that it is to
replace the data that was passed in. If the function doesn't return
anything, nothing else is affected.

::

    def record_hook(r, *args, **kwargs):
        r.hook_called = True
        return r

Let's print some request method arguments at runtime::

    >>> niquests.get('https://httpbin.org/', hooks={'response': print_url})
    https://httpbin.org/
    <Response HTTP/2 [200]>

You can add multiple hooks to a single request.  Let's call two hooks at once::

    >>> r = niquests.get('https://httpbin.org/', hooks={'response': [print_url, record_hook]})
    >>> r.hook_called
    True

You can also add hooks to a ``Session`` instance.  Any hooks you add will then
be called on every request made to the session.  For example::

   >>> s = niquests.Session()
   >>> s.hooks['response'].append(print_url)
   >>> s.get('https://httpbin.org/')
    https://httpbin.org/
    <Response HTTP/2 [200]>

A ``Session`` can have multiple hooks, which will be called in the order
they are added.

You can find a example of how to retrieve the connection information just before the request is sent::

    >>> r = niquests.get("https://1.1.1.1", hooks={"pre_send": [lambda r: print(r.conn_info)]}

Here, ``r`` is the ``PreparedRequest`` and ``conn_info`` contains a ``ConnectionInfo``.
You can explore the following data in it.

- **certificate_der**: The peer certificate in DER format (binary)
- **certificate_dict**: The peer certificate as a dictionary like ``ssl.SSLSocket.getpeercert(binary_from=False)`` output it.
- **tls_version**: TLS version.
- **cipher**: Cipher used.
- **http_version**: Http version that is about to be used.
- **destination_address**: The remote peer address given to us by the DNS resolver.
- **issuer_certificate_der**: Immediate issuer (in the TLS certificate chain) in DER format (binary)
- **issuer_certificate_dict**: Immediate issuer (in the TLS certificate chain) as a dictionary
- **established_latency**: The amount of time consumed to get an ESTABLISHED network link.
- **resolution_latency**: The amount of time consumed for the hostname resolution.
- **tls_handshake_latency**: The amount of time consumed for the TLS handshake completion.
- **request_sent_latency**: The amount of time consumed to encode and send the whole request through the socket.

.. warning:: Depending on your platform and interpreter, some key element might not be available and be assigned ``None`` everytime. Like **certificate_dict** on MacOS.

List of tangible use-cases:


- Displaying cool stuff on the screen for CLI based tools.
- Also debugging, obviously.
- Among others thing.

.. note:: In a asynchronous HTTP request, you may pass awaitable functions in addition to the usual synchronous ones.

Track upload progress
---------------------

You may use the ``on_upload`` hook to track the upload progress of a request.
The callable will receive the ``PreparedRequest`` that will contain a property named ``upload_progress``.

.. note:: ``upload_progress`` is a ``TransferProgress`` instance.

You may find bellow a plausible example::

    import niquests

    if __name__ == "__main__":
        def track(req):
            print(req.upload_progress)

        with niquests.Session() as s:
            s.post("https://pie.dev/post", data=b"foo"*16800*1024, hooks={"on_upload": [track]})

.. note:: Niquests recommend the excellent tqdm library to create progress bars with ease.

``upload_progress`` contains the following properties:


- **percentage** (optional) Basic percentage expressed via float from 0% to 100%
- **content_length** (optional) The expected total bytes to be sent (may be unset due to some body formats, e.g. blind iterator / generator)
- **total** : Amount of bytes sent to the remote peer
- **is_completed** : Determine if the transfer ended
- **any_error** : Simple boolean that indicate whenever a error occurred during transfer (like early response from peer)

.. _custom-auth:

Custom Authentication
---------------------

Niquests allows you to specify your own authentication mechanism.

Any callable which is passed as the ``auth`` argument to a request method will
have the opportunity to modify the request before it is dispatched.

Authentication implementations are subclasses of :class:`AuthBase <niquests.auth.AuthBase>`,
and are easy to define. Niquests provides two common authentication scheme
implementations in ``niquests.auth``: :class:`HTTPBasicAuth <niquests.auth.HTTPBasicAuth>` and
:class:`HTTPDigestAuth <niquests.auth.HTTPDigestAuth>`.

Let's pretend that we have a web service that will only respond if the
``X-Pizza`` header is set to a password value. Unlikely, but just go with it.

::

    from niquests.auth import AuthBase

    class PizzaAuth(AuthBase):
        """Attaches HTTP Pizza Authentication to the given Request object."""
        def __init__(self, username):
            # setup any auth-related data here
            self.username = username

        def __call__(self, r):
            # modify and return the request
            r.headers['X-Pizza'] = self.username
            return r

Then, we can make a request using our Pizza Auth::

    >>> niquests.get('http://pizzabin.org/admin', auth=PizzaAuth('kenneth'))
    <Response HTTP/2 [200]>

.. note:: In case you want a clever shortcut to passing a ``Bearer`` token, you can pass directly (as a string) the token to ``auth=...`` instead.

.. _streaming-requests:

Streaming Requests
------------------

With :meth:`Response.iter_lines() <niquests.Response.iter_lines>` you can easily
iterate over streaming APIs such as the `Twitter Streaming
API <https://dev.twitter.com/streaming/overview>`_. Simply
set ``stream`` to ``True`` and iterate over the response with
:meth:`~niquests.Response.iter_lines()`::

    import json
    import niquests

    r = niquests.get('https://httpbin.org/stream/20', stream=True)

    for line in r.iter_lines():

        # filter out keep-alive new lines
        if line:
            decoded_line = line.decode('utf-8')
            print(json.loads(decoded_line))

When using `decode_unicode=True` with
:meth:`Response.iter_lines() <niquests.Response.iter_lines>` or
:meth:`Response.iter_content() <niquests.Response.iter_content>`, you'll want
to provide a fallback encoding in the event the server doesn't provide one::

    r = niquests.get('https://httpbin.org/stream/20', stream=True)

    if r.encoding is None:
        r.encoding = 'utf-8'

    for line in r.iter_lines(decode_unicode=True):
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

If you need to use a proxy, you can configure individual requests with the
``proxies`` argument to any request method::

    import niquests

    proxies = {
      'http': 'http://10.10.1.10:3128',
      'https': 'http://10.10.1.10:1080',
    }

    niquests.get('http://example.org', proxies=proxies)

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

.. warning::  Setting ``session.proxies`` may behave differently than expected.
    Values provided will be overwritten by environmental proxies
    (those returned by `urllib.request.getproxies <https://docs.python.org/3/library/urllib.request.html#urllib.request.getproxies>`_).
    To ensure the use of proxies in the presence of environmental proxies,
    explicitly specify the ``proxies`` argument on all individual requests as
    initially explained above.

    See `#2018 <https://github.com/psf/requests/issues/2018>`_ for details.

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
    print(generate_ca_bundle)  # it is a single concatenated list of PEM (string)

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
as using a HTTP one::

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

When you receive a response, Niquests makes a guess at the encoding to
use for decoding the response when you access the :attr:`Response.text
<niquests.Response.text>` attribute. Niquests will first check for an
encoding in the HTTP header, and if none is present or if specified is invalid,
will use `charset_normalizer <https://pypi.org/project/charset_normalizer/>`_
to attempt to guess the encoding.

If you require a different encoding, you can
manually set the :attr:`Response.encoding <niquests.Response.encoding>`
property, or use the raw :attr:`Response.content <niquests.Response.content>`.

You should keep in mind that if Niquests fail to choose a suitable encoding,
the ``text`` method from ``Response`` will return ``None``. This is the default
since the version 3.
We choose to return None in those cases because of numerous things, like for example:

- Avoid accidentally decoding a large binary.
- Avoid rare type of attacks where hacker expect you to decode an invalid payload and expect you to be non-strict.

.. _http-verbs:

HTTP Verbs
----------

Niquests provides access to almost the full range of HTTP verbs: GET, OPTIONS,
HEAD, POST, PUT, PATCH and DELETE. The following provides detailed examples of
using these various verbs in Niquests, using the GitHub API.

We will begin with the verb most commonly used: GET. HTTP GET is an idempotent
method that returns a resource from a given URL. As a result, it is the verb
you ought to use when attempting to retrieve data from a web location. An
example usage would be attempting to get information about a specific commit
from GitHub. Suppose we wanted commit ``a050faf`` on Niquests. We would get it
like so::

    >>> import niquests
    >>> r = niquests.get('https://api.github.com/repos/psf/requests/git/commits/a050faf084662f3a352dd1a941f2c7c9f886d4ad')

We should confirm that GitHub responded correctly. If it has, we want to work
out what type of content it is. Do this like so::

    >>> if r.status_code == niquests.codes.ok:
    ...     print(r.headers['content-type'])
    ...
    application/json; charset=utf-8

So, GitHub returns JSON. That's great, we can use the :meth:`r.json
<niquests.Response.json>` method to parse it into Python objects.

::

    >>> commit_data = r.json()

    >>> print(commit_data.keys())
    ['committer', 'author', 'url', 'tree', 'sha', 'parents', 'message']

    >>> print(commit_data['committer'])
    {'date': '2012-05-10T11:10:50-07:00', 'email': 'me@kennethreitz.com', 'name': 'Kenneth Reitz'}

    >>> print(commit_data['message'])
    makin' history

So far, so simple. Well, let's investigate the GitHub API a little bit. Now,
we could look at the documentation, but we might have a little more fun if we
use Niquests instead. We can take advantage of the Niquests OPTIONS verb to
see what kinds of HTTP methods are supported on the url we just used.

::

    >>> verbs = niquests.options(r.url)
    >>> verbs.status_code
    500

Uh, what? That's unhelpful! Turns out GitHub, like many API providers, don't
actually implement the OPTIONS method. This is an annoying oversight, but it's
OK, we can just use the boring documentation. If GitHub had correctly
implemented OPTIONS, however, they should return the allowed methods in the
headers, e.g.

::

    >>> verbs = niquests.options('http://a-good-website.com/api/cats')
    >>> print(verbs.headers['allow'])
    GET,HEAD,POST,OPTIONS

Turning to the documentation, we see that the only other method allowed for
commits is POST, which creates a new commit. As we're using the Niquests repo,
we should probably avoid making ham-handed POSTS to it. Instead, let's play
with the Issues feature of GitHub.

This documentation was added in response to
`Issue #482 <https://github.com/psf/requests/issues/482>`_. Given that
this issue already exists, we will use it as an example. Let's start by getting it.

::

    >>> r = niquests.get('https://api.github.com/repos/psf/requests/issues/482')
    >>> r.status_code
    200

    >>> issue = json.loads(r.text)

    >>> print(issue['title'])
    Feature any http verb in docs

    >>> print(issue['comments'])
    3

Cool, we have three comments. Let's take a look at the last of them.

::

    >>> r = niquests.get(r.url + '/comments')
    >>> r.status_code
    200

    >>> comments = r.json()

    >>> print(comments[0].keys())
    ['body', 'url', 'created_at', 'updated_at', 'user', 'id']

    >>> print(comments[2]['body'])
    Probably in the "advanced" section

Well, that seems like a silly place. Let's post a comment telling the poster
that he's silly. Who is the poster, anyway?

::

    >>> print(comments[2]['user']['login'])
    kennethreitz

OK, so let's tell this Kenneth guy that we think this example should go in the
quickstart guide instead. According to the GitHub API doc, the way to do this
is to POST to the thread. Let's do it.

::

    >>> body = json.dumps({u"body": u"Sounds great! I'll get right on it!"})
    >>> url = u"https://api.github.com/repos/psf/requests/issues/482/comments"

    >>> r = niquests.post(url=url, data=body)
    >>> r.status_code
    404

Huh, that's weird. We probably need to authenticate. That'll be a pain, right?
Wrong. Niquests makes it easy to use many forms of authentication, including
the very common Basic Auth.

::

    >>> from niquests.auth import HTTPBasicAuth
    >>> auth = HTTPBasicAuth('fake@example.com', 'not_a_real_password')

    >>> r = niquests.post(url=url, data=body, auth=auth)
    >>> r.status_code
    201

    >>> content = r.json()
    >>> print(content['body'])
    Sounds great! I'll get right on it.

Brilliant. Oh, wait, no! I meant to add that it would take me a while, because
I had to go feed my cat. If only I could edit this comment! Happily, GitHub
allows us to use another HTTP verb, PATCH, to edit this comment. Let's do
that.

::

    >>> print(content[u"id"])
    5804413

    >>> body = json.dumps({u"body": u"Sounds great! I'll get right on it once I feed my cat."})
    >>> url = u"https://api.github.com/repos/psf/requests/issues/comments/5804413"

    >>> r = niquests.patch(url=url, data=body, auth=auth)
    >>> r.status_code
    200

Excellent. Now, just to torture this Kenneth guy, I've decided to let him
sweat and not tell him that I'm working on this. That means I want to delete
this comment. GitHub lets us delete comments using the incredibly aptly named
DELETE method. Let's get rid of it.

::

    >>> r = niquests.delete(url=url, auth=auth)
    >>> r.status_code
    204
    >>> r.headers['status']
    '204 No Content'

Excellent. All gone. The last thing I want to know is how much of my ratelimit
I've used. Let's find out. GitHub sends that information in the headers, so
rather than download the whole page I'll send a HEAD request to get the
headers.

::

    >>> r = niquests.head(url=url, auth=auth)
    >>> print(r.headers)
    ...
    'x-ratelimit-remaining': '4995'
    'x-ratelimit-limit': '5000'
    ...

Excellent. Time to write a Python program that abuses the GitHub API in all
kinds of exciting ways, 4995 more times.

.. _custom-verbs:

Custom Verbs
------------

From time to time you may be working with a server that, for whatever reason,
allows use or even requires use of HTTP verbs not covered above. One example of
this would be the MKCOL method some WEBDAV servers use. Do not fret, these can
still be used with Niquests. These make use of the built-in ``.request``
method. For example::

    >>> r = niquests.request('MKCOL', url, data=data)
    >>> r.status_code
    200 # Assuming your call was correct

Utilising this, you can make use of any method verb that your server allows.


.. _link-headers:

Link Headers
------------

Many HTTP APIs feature Link headers. They make APIs more self describing and
discoverable.

GitHub uses these for `pagination <https://developer.github.com/v3/#pagination>`_
in their API, for example::

    >>> url = 'https://api.github.com/users/kennethreitz/repos?page=1&per_page=10'
    >>> r = niquests.head(url=url)
    >>> r.headers['link']
    '<https://api.github.com/users/kennethreitz/repos?page=2&per_page=10>; rel="next", <https://api.github.com/users/kennethreitz/repos?page=6&per_page=10>; rel="last"'

Niquests will automatically parse these link headers and make them easily consumable::

    >>> r.links["next"]
    {'url': 'https://api.github.com/users/kennethreitz/repos?page=2&per_page=10', 'rel': 'next'}

    >>> r.links["last"]
    {'url': 'https://api.github.com/users/kennethreitz/repos?page=7&per_page=10', 'rel': 'last'}

.. _transport-adapters:

Transport Adapters
------------------

As of v1.0.0, Niquests has moved to a modular internal design. Part of the
reason this was done was to implement Transport Adapters, originally
`described here`_. Transport Adapters provide a mechanism to define interaction
methods for an HTTP service. In particular, they allow you to apply per-service
configuration.

Niquests ships with a single Transport Adapter, the :class:`HTTPAdapter
<niquests.adapters.HTTPAdapter>`. This adapter provides the default Niquests
interaction with HTTP and HTTPS using the powerful `urllib3.future`_ library. Whenever
a Niquests :class:`Session <niquests.Session>` is initialized, one of these is
attached to the :class:`Session <niquests.Session>` object for HTTP, and one
for HTTPS.

Niquests enables users to create and use their own Transport Adapters that
provide specific functionality. Once created, a Transport Adapter can be
mounted to a Session object, along with an indication of which web services
it should apply to.

::

    >>> s = niquests.Session()
    >>> s.mount('https://github.com/', MyAdapter())

The mount call registers a specific instance of a Transport Adapter to a
prefix. Once mounted, any HTTP request made using that session whose URL starts
with the given prefix will use the given Transport Adapter.

.. note:: The adapter will be chosen based on a longest prefix match. Be mindful
   prefixes such as ``http://localhost`` will also match ``http://localhost.other.com``
   or ``http://localhost@other.com``. It's recommended to terminate full hostnames with a ``/``.

Many of the details of implementing a Transport Adapter are beyond the scope of
this documentation, but take a look at the next example for a simple SSL use-
case. For more than that, you might look at subclassing the
:class:`BaseAdapter <niquests.adapters.BaseAdapter>`.

Example: Specific SSL Version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Niquests team has made a specific choice to use whatever SSL version is
default in the underlying library (`urllib3.future`_). Normally this is fine, but from
time to time, you might find yourself needing to connect to a service-endpoint
that uses a version that isn't compatible with the default.

You can use Transport Adapters for this by taking most of the existing
implementation of HTTPAdapter, and adding a parameter *ssl_version* that gets
passed-through to `urllib3.future`. We'll make a Transport Adapter that instructs the
library to use SSLv3::

    import ssl
    from urllib3.poolmanager import PoolManager

    from niquests.adapters import HTTPAdapter


    class Ssl3HttpAdapter(HTTPAdapter):
        """"Transport adapter" that allows us to use SSLv3."""

        def init_poolmanager(self, connections, maxsize, block=False):
            self.poolmanager = PoolManager(
                num_pools=connections, maxsize=maxsize,
                block=block, ssl_version=ssl.PROTOCOL_SSLv3)

Example: Automatic Retries
~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, Niquests does not retry failed connections. However, it is possible
to implement automatic retries with a powerful array of features, including
backoff, within a Niquests :class:`Session <niquests.Session>` using the
`urllib3.util.Retry`_ class::

    from urllib3.util import Retry
    from niquests import Session

    retries = Retry(
        total=3,
        backoff_factor=0.1,
        status_forcelist=[502, 503, 504],
        allowed_methods={'POST'},
    )

    s = Session(retries=retries)
    s.get("https://1.1.1.1")

.. _`described here`: https://kenreitz.org/essays/2012/06/14/the-future-of-python-http
.. _`urllib3.future`: https://github.com/jawah/urllib3.future
.. _`urllib3.util.Retry`: https://urllib3-future.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry

.. _blocking-or-nonblocking:

Blocking Or Non-Blocking?
-------------------------

The :attr:`Response.content <niquests.Response.content>`
property will block until the entire response has been downloaded by default in HTTP/1.1
In HTTP/2 onward, non-consumed response (body, aka. stream=True) will no longer block the connection.

But if you leverage a full multiplexed connection, Niquests no longer block your synchronous
loop. You are free of the IO blocking per request.

You may also use the ``AsyncSession`` that provide you with the same methods as the regular
``Session`` but with asyncio support.

Header Ordering
---------------

In unusual circumstances you may want to provide headers in an ordered manner. If you pass an ``OrderedDict`` to the ``headers`` keyword argument, that will provide the headers with an ordering. *However*, the ordering of the default headers used by Niquests will be preferred, which means that if you override default headers in the ``headers`` keyword argument, they may appear out of order compared to other headers in that keyword argument.

If this is problematic, users should consider setting the default headers on a :class:`Session <niquests.Session>` object, by setting :attr:`Session.headers <niquests.Session.headers>` to a custom ``OrderedDict``. That ordering will always be preferred.

.. _timeouts:

Timeouts
--------

Most requests to external servers should have a timeout attached, in case the
server is not responding in a timely manner. By default, requests do not time
out unless a timeout value is set explicitly. Without a timeout, your code may
hang for minutes.

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

If you specify a single value for the timeout, like this::

    r = niquests.get('https://github.com', timeout=5)

The timeout value will be applied to both the ``connect`` and the ``read``
timeouts. Specify a tuple if you would like to set the values separately::

    r = niquests.get('https://github.com', timeout=(3.05, 27))

If the remote server is very slow, you can tell Niquests to wait forever for
a response, by passing None as a timeout value and then retrieving a cup of
coffee.::

    r = niquests.get('https://github.com', timeout=None)

It is also possible to use the ``Timeout`` class from ``urllib3`` directly::

    from urllib3 import Timeout

    r = niquests.get('https://github.com', timeout=Timeout(3, 9))

.. _`connect()`: https://linux.die.net/man/2/connect

OCSP or Certificate Revocation
------------------------------

Difficult subject. Short story, when a HTTP client establish a secure connection,
it verify that the certificate is valid. The problem is that a certificate
can be both valid and revoked due its immutability, the revocation status must
be taken from an outside source, most of the revocation are linked to a hack/security violation.

Niquests try to protect you from the evoked problem by doing a post-handshake verification
using the OCSP protocols via plain HTTP.

Unfortunately, at this moment, no bullet proof solution has emerged against revoked certificate.
We are aware of this. But still, it is better than nothing!

By default, Niquests operate a soft-fail verification, or non-strict if you prefer.

This feature is broadly available and is enabled by default when ``verify=True``.
We decided to follow what browsers do by default, so Niquests follows by being non-strict.
OCSP responses are expected to arrive in less than 200ms, otherwise ignored (e.g. OCSP is dropped).
Niquests keeps in-memory the results until the size exceed 2,048 entries, then an algorithm choose an entry
to be deleted (oldest request or the first one that ended in error).

You can at your own discretion enable strict OCSP checks by passing the environment variable ``NIQUESTS_STRICT_OCSP``
with anything inside but ``0``. In strict mode the maximum delay for response passes from 200ms to 1,000ms and
raises an error or explicit warning.

In non-strict mode, this security measure will be deactivated automatically if your usage is unreasonable.
e.g. Making a hundred of requests to a hundred of domains, thus consuming resources that should have been
allocated to browser users. This was made available for users with a limited target of domains to get
a complementary security measure.

Unless in strict-mode, the proxy configuration will be respected when given, as long as it specify
a plain ``http`` proxy. This is meant for people who want privacy.

This feature may not be available if the ``qh3`` package is missing from your environment.
Verify the availability by running ``python -m niquests.help``.

.. note:: Access property ``ocsp_verified`` in both ``PreparedRequest``, and ``Response`` to have information about this post handshake verification.

Specify HTTP/3 capable endpoint preemptively
--------------------------------------------

Preemptively register a website to be HTTP/3 capable prior to the first TLS over TCP handshake.
You can do so by doing like::

    from niquests import Session

    s = Session()
    s.quic_cache_layer.add_domain("cloudflare.com")

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

In immediate opposition to the previous section::

    from niquests import Session

    s = Session()
    s.quic_cache_layer.exclude_domain("cloudflare.com")

This will prevent the auto-upgrade to HTTP/3 via the Alt-Svc headers.

.. note:: This is most useful for people that encounter a server that yield its support for HTTP/3 while not able to. This permit to isolate the bad server instead of disabling HTTP/3 session-wide.

Increase the default Alt-Svc cache size
---------------------------------------

When a server yield its support for HTTP/3 over QUIC, the information
is stored within a local thread safe in-memory storage.

That storage is limited to 12,288 entries by default, and you can override this
by passing a custom ``QuicSharedCache`` instance like so::

    import niquests

    cache = niquests.structures.QuicSharedCache(max_size=128_000)
    session = niquests.Session(quic_cache_layer=cache)


.. note:: Passing ``None`` to max size actually permit the cache to grow indefinitely. This is unwise and can lead to significant RAM usage.

When the cache is full, the oldest entry is removed.

Disable HTTP/1.1, HTTP/2, and/or HTTP/3
-----------------------------

You can at your own discretion disable a protocol by passing ``disable_http2=True`` or
``disable_http3=True`` within your ``Session`` constructor.

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
    r.version  # 20 (aka. HTTP/2)

.. note:: You may do the same for servers that do not support the ALPN extension for https URLs.

.. warning:: Disabling HTTP/1.1 and HTTP/2 will raise an error (RuntimeError) for non https URLs! As HTTP/3 is designed for the QUIC layer, which itself is based on TLS 1.3.

Thread Safety
-------------

Niquests is meant to be thread and task safe. Any error or unattended behaviors are covered by our support for bug policy.
Both main scenarios are eligible, meaning Thread and Async, with Thread and Sync.

Support include notable performance issues like abusive lock.

Use a custom CA without loosing the official ones
-------------------------------------------------

There's an interesting use-case where a user may want to be able to request both private
and public HTTP endpoints without doing some gymnastic with ``verify=...``.

Thanks to our underlying library ``wassima`` you can register globally your own set
of certificate authorities like so::

    import wassima

    wassima.register_ca(my_own_ca_pem_str)

That's it! Niquests will now automatically recognize it and use it to verify your secure endpoints.
You'll have to register it prior to your HTTP requests.

.. note:: While doing local development with HTTPS, we recommend using tool like ``mkcert`` that will register the CA into your local machine trust store. Niquests is natively capable of picking them up.

Disable either IPv4 or IPv6
---------------------------

You may be interested in controlling what kind of address you would accept connecting to.
Since Niquests 3.4+, you can configure that aspect per ``Session`` instance.

Having a session without IPv6 enabled should be done that way::

    import niquests

    session = niquests.Session(disable_ipv6=True)

.. warning:: You cannot set both ``disable_ipv4`` and ``disable_ipv6`` at the cost of receiving a RuntimeError exception.

Setting the source network adapter
----------------------------------

In a complex scenario, you could face the following: "I have multiple network adapters, some can access this and other that.."
Since Niquests 3.4+, you can configure that aspect per ``Session`` instance.

Having a session that explicitly bind to "10.10.4.1" on port 4444 should be done that way::

    import niquests

    session = niquests.Session(source_address=("10.10.4.1", 4444))

It will be passed down the the lower stack. No effort required.

.. note:: You can set **0** instead of 4444 to select a random port.

.. note:: You can set **0.0.0.0** to select the network adapter automatically instead, if you wish to set the port only.

Inspect network timings
-----------------------

You are probably used to calling ``response.elapsed`` to get a rough estimate on how long did the
request took to complete.

It is likely that you may be interested in knowing:

- How long did the TCP/UDP established connection took?
- How long did the DNS resolution cost me?

... and so on.

Here is a simple example::

    import niquests

    session = niquests.Session()

    response = session.get("https://pie.dev/get")

    print(response.conn_info.resolution_latency)  # output the DNS resolution latency
    print(response.conn_info.tls_handshake_latency)  # the TLS handshake completion

Here, ``conn_info`` is a ``urllib3.ConnectionInfo`` instance. The complete list of
attributes is listed on the Hook bottom section.

.. note:: Each response and request are linked to a unique ConnectionInfo.

Verify Certificate Fingerprint
------------------------------

.. note:: Available since Niquests 3.5.4

An alternative to the certificate verification can be asserting its fingerprint. We (absolutely) do
not recommend using it unless you are left with no other alternative.

Here is a simple example::

    import niquests

    session = niquests.Session()
    session.get("https://pie.dev/get", verify="sha256_8fff956b66667ffe5801c8432b12c367254727782d91bc695b7a53d0b512d721")

.. warning:: Supported fingerprinting algorithms are sha256, and sha1. The prefix is mandatory.

TLS Fingerprint (like JA3)
--------------------------

Some of you seems to be interested in that topic, at least according to the statistics presented to me.
Niquests is dedicated to providing a software that present a unique and close enough signature (against modern browser)
that you should be protected against TLS censorship / blocking technics.

We are actively working toward a way to permanently improving this.
To help us fighting toward the greater good, feel free to sponsor us and/or speaking out loud about your
experiences, whether about a specific country practices or global ISP/Cloud provider ones.

.. note:: If you are getting blocked, come and get in touch with us through our Github issues.

Tracking the real download speed
--------------------------------

In a rare case, you may be left with no clue on what is the real "download speed" due to the
remote server applying a "transfer-encoding" or also know as compressing (zstd, br or gzip).

Niquests automatically decompress response bodies, so doing a call to ``iter_content`` is not going to yield
the size actually extracted from the socket but rather from the decompressor algorithm.

To remediate this issue we've implemented a new property into your ``Response`` object. Named ``download_progress``
that is a ``TransferProgress`` instance.

.. warning:: This feature is enabled when ``stream=True``.

Here is a basic example of how you would proceed::

    import niquests

    with niquests.Session() as s:
        with s.get("https://ash-speed.hetzner.com/100MB.bin", stream=True) as r:
            for chunk in r.iter_content():
                # do anything you want with chunk
                print(r.download_progress.total)  # this actually contain the amt of bytes (raw) downloaded from the socket.

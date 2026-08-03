.. _quickstart:

Quickstart
==========

.. module:: niquests.models

Eager to get started? This page gives a good introduction to getting started
with Niquests.

First, make sure that:

* Niquests is :ref:`installed <install>`
* Niquests is :ref:`up-to-date <updates>`

Let's get started with some simple examples.

.. note::

    Standalone async examples must be enclosed in an async function and started
    with :func:`asyncio.run`. Short async snippets below may be pasted into the
    body of the documented ``main()`` wrapper.

    .. code:: python

        import asyncio
        import niquests

        async def main() -> None:
            """Paste the example code here."""

        if __name__ == "__main__":
            asyncio.run(main())


Make a request
--------------

Making a request with Niquests is very simple.

Begin by importing the Niquests module:

.. code:: python

    import niquests

Now, let's try to get a webpage. For this example, let's get GitHub's public
timeline.

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.get('https://api.github.com/events')

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.aget('https://api.github.com/events')

Now, we have a :class:`Response <niquests.Response>` object called ``r``. We can
get all the information we need from this object.

Niquests' simple API makes all forms of HTTP requests straightforward. For
example, this is how you make an HTTP POST request:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.post('https://httpbingo.org/post', data={'key': 'value'})

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.apost('https://httpbingo.org/post', data={'key': 'value'})

Nice, right? What about the other HTTP request methods: PUT, PATCH, DELETE,
HEAD, OPTIONS, and QUERY? These are all just as simple:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.put('https://httpbingo.org/put', data={'key': 'value'})
        r = niquests.patch('https://httpbingo.org/patch', data={'key': 'value'})
        r = niquests.delete('https://httpbingo.org/delete')
        r = niquests.head('https://httpbingo.org/get')
        r = niquests.options('https://httpbingo.org/get')
        r = niquests.query('https://httpbingo.org/anything', json={'key': 'value'})

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.aput('https://httpbingo.org/put', data={'key': 'value'})
        r = await niquests.apatch('https://httpbingo.org/patch', data={'key': 'value'})
        r = await niquests.adelete('https://httpbingo.org/delete')
        r = await niquests.ahead('https://httpbingo.org/get')
        r = await niquests.aoptions('https://httpbingo.org/get')
        r = await niquests.aquery('https://httpbingo.org/anything', json={'key': 'value'})

``QUERY``, standardized by :rfc:`10008`, carries a query in the request body.
Like ``GET``, it is safe and idempotent; unlike ``GET``, it can carry content.
Use :meth:`Session.query() <niquests.Session.query>` or
:meth:`AsyncSession.query() <niquests.AsyncSession.query>` when working with a session.

That's all well and good, but it's also only the start of what Niquests can
do.

Passing parameters in URLs
--------------------------

You often want to send some sort of data in the URL's query string. If
you were constructing the URL by hand, this data would be given as key/value
pairs in the URL after a question mark, e.g. ``httpbingo.org/get?key=val``.
Niquests allows you to provide these arguments as a dictionary of strings,
using the ``params`` keyword argument. As an example, if you wanted to pass
``key1=value1`` and ``key2=value2`` to ``httpbingo.org/get``, you would use the
following code:

.. tab:: 🔂 Sync

    .. code:: python

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = niquests.get('https://httpbingo.org/get', params=payload)

.. tab:: 🔀 Async

    .. code:: python

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = await niquests.aget('https://httpbingo.org/get', params=payload)

You can see that the URL has been correctly encoded by printing the URL:

.. code:: python

    print(r.url)  # 'https://httpbingo.org/get?key1=value1&key2=value2'

Note that any dictionary key whose value is ``None`` will not be added to the
URL's query string.

You can also pass a list of items as a value:

.. tab:: 🔂 Sync

    .. code:: python

        payload = {'key1': 'value1', 'key2': ['value2', 'value3']}
        r = niquests.get('https://httpbingo.org/get', params=payload)

        print(r.url)  # 'https://httpbingo.org/get?key1=value1&key2=value2&key2=value3'

.. tab:: 🔀 Async

    .. code:: python

        payload = {'key1': 'value1', 'key2': ['value2', 'value3']}
        r = await niquests.aget('https://httpbingo.org/get', params=payload)

        print(r.url)  # 'https://httpbingo.org/get?key1=value1&key2=value2&key2=value3'

Response content
----------------

We can read the content of the server's response. Consider the GitHub timeline
again:

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        r = niquests.get('https://api.github.com/events')
        print(r.text)  # '[{"repository":{"open_issues":0,"url":"https://github.com/...

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        r = await niquests.aget('https://api.github.com/events')
        print(r.text)  # '[{"repository":{"open_issues":0,"url":"https://github.com/...

Niquests automatically decodes content from the server. Most Unicode character
sets are decoded seamlessly.

When you make a request, Niquests makes educated guesses about the encoding of
the response based on the HTTP headers. The text encoding guessed by Niquests
is used when you access :attr:`r.text <niquests.Response.text>`. You can inspect and
change it through the :attr:`r.encoding <niquests.Response.encoding>` property:

.. code:: python

    print(r.encoding)  # 'utf-8'

    r.encoding = 'ISO-8859-1'  # Force a specific encoding.

.. warning:: If Niquests cannot decode the content to a string with confidence,
   it returns ``None``.

If you change the encoding, Niquests will use the new value of
:attr:`r.encoding <niquests.Response.encoding>` whenever you access
:attr:`r.text <niquests.Response.text>`. You might do this when
you can apply special logic to work out what the encoding of the content will
be. For example, HTML and XML can specify their encoding in their bodies. In
situations like this, use :attr:`r.content <niquests.Response.content>` to find the
encoding, and then set :attr:`r.encoding <niquests.Response.encoding>`. This will let
you use :attr:`r.text <niquests.Response.text>` with
the correct encoding.

Niquests will also use custom encodings if you need them. If
you have created your own encoding and registered it with the :mod:`codecs`
module, you can simply use the codec name as the value of
:attr:`r.encoding <niquests.Response.encoding>` and
Niquests will handle the decoding for you.

Binary response content
-----------------------

You can also access the response body as bytes, for non-text requests::

    >>> r.content
    b'[{"repository":{"open_issues":0,"url":"https://github.com/...

The ``gzip`` and ``deflate`` content codings are automatically decoded for you.

The ``br`` content coding is automatically decoded for you if a Brotli library
like `brotli <https://pypi.org/project/brotli>`_ or `brotlicffi <https://pypi.org/project/brotlicffi>`_ is installed.

The ``zstd`` content coding is automatically decoded for you if the
`zstandard <https://pypi.org/project/zstandard>`_ library is installed.

For example, to create an image from binary data returned by a request, you can
use the following code::

    >>> from PIL import Image
    >>> from io import BytesIO

    >>> i = Image.open(BytesIO(r.content))

JSON response content
---------------------

There's also a built-in JSON decoder for JSON data:

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        r = niquests.get('https://api.github.com/events')
        print(r.json())  # [{'repository': {'open_issues': 0, 'url': 'https://github.com/...

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        r = await niquests.aget('https://api.github.com/events')
        print(r.json())  # [{'repository': {'open_issues': 0, 'url': 'https://github.com/...

In case the JSON decoding fails, :meth:`r.json() <niquests.Response.json>` raises an exception. For example, if
the response gets a 204 (No Content), or if the response contains invalid JSON,
attempting :meth:`r.json() <niquests.Response.json>` raises
:exc:`~niquests.exceptions.JSONDecodeError`. This wrapper exception
provides interoperability for multiple exceptions that may be thrown by different
Python versions and JSON serialization libraries.
:meth:`Response.json() <niquests.Response.json>` attempts
to parse the response body regardless of its ``Content-Type`` header.

The success of a call to :meth:`r.json() <niquests.Response.json>` does **not**
indicate the success of the response. Some servers may return a JSON object in a
failed response (e.g. error details with HTTP 500). Such JSON will be decoded
and returned. To check that a request is successful, use
:meth:`r.raise_for_status() <niquests.Response.raise_for_status>` or check that
:attr:`r.status_code <niquests.Response.status_code>` is what you expect.

.. note:: Since Niquests 3.2,
   :meth:`r.raise_for_status() <niquests.Response.raise_for_status>` is chainable because it
   returns the response when no error is raised.

.. tip:: Niquests supports using ``orjson`` instead of the :mod:`json` standard
   library. To use that feature, install ``orjson`` or ``niquests[speedups]``.
   This can dramatically improve performance.

.. tip:: For typed JSON deserialization (e.g. with ``msgspec``, ``pydantic``, or ``cattrs``),
   use :attr:`r.content <niquests.Response.content>` directly instead of
   :meth:`r.json() <niquests.Response.json>` for significantly better performance.
   For example, ``msgspec.json.decode(r.content, type=list[User])`` decodes bytes into typed
   objects in a single pass, avoiding the intermediate dict. This is 2-5x faster than
   ``msgspec.convert(r.json(), list[User])``.

Raw response content
--------------------

In the rare case that you'd like to get the raw socket response from the
server, you can access :attr:`r.raw <niquests.Response.raw>`. If you want to do this,
make sure you set
``stream=True`` in your initial request. Once you do, you can do this:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.get('https://api.github.com/events', stream=True)

        r.raw
        # <urllib3.response.HTTPResponse object at ...>

        r.raw.read(10)
        # b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.aget('https://api.github.com/events', stream=True)

        r.raw
        # <urllib3._async.response.AsyncHTTPResponse object at ...>

        await r.raw.read(10)
        # b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'


In general, however, you should use a pattern like this to save what is being
streamed to a file:

.. tab:: 🔂 Sync

    .. code:: python

        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)

.. tab:: 🔀 Async

    .. code:: python

        with open(filename, 'wb') as fd:
            async for chunk in await r.iter_content(chunk_size=128):
                fd.write(chunk)

    .. warning:: Consider ``aiofiles`` or a similar library to avoid blocking
       file I/O in async code.

Using :meth:`Response.iter_content <niquests.Response.iter_content>` will handle a lot
of what you would otherwise have to handle when using
:attr:`Response.raw <niquests.Response.raw>` directly. When streaming a
download, the above is the preferred and recommended way to retrieve the
content. Note that ``chunk_size`` can be freely adjusted to a number that
may better fit your use cases.

.. note::

   An important note about using
   :meth:`Response.iter_content <niquests.Response.iter_content>` versus
   :attr:`Response.raw <niquests.Response.raw>`.
   :meth:`Response.iter_content <niquests.Response.iter_content>` will automatically
   decode the ``gzip`` and ``deflate`` content codings.
   :meth:`Response.iter_raw <niquests.Response.iter_raw>` is a raw stream of bytes; it does not
   transform the response content. If you really need access to the bytes as they
   were returned, use :meth:`Response.iter_raw <niquests.Response.iter_raw>`.


Custom headers
--------------

To add HTTP fields to a request, pass a dictionary to the
``headers`` parameter.

For example, we didn't specify our user-agent in the previous example:

.. tab:: 🔂 Sync

    .. code:: python

        url = 'https://api.github.com/some/endpoint'
        headers = {'user-agent': 'my-app/0.0.1'}

        r = niquests.get(url, headers=headers)

.. tab:: 🔀 Async

    .. code:: python

        url = 'https://api.github.com/some/endpoint'
        headers = {'user-agent': 'my-app/0.0.1'}

        r = await niquests.aget(url, headers=headers)

Custom headers have lower precedence than more specific sources of information.
For example:

* Authorization headers set with ``headers=`` will be overridden if credentials
  are specified in ``.netrc``, which in turn will be overridden by the ``auth=``
  parameter. Niquests searches for the netrc file at ``~/.netrc``, ``~/_netrc``,
  or at the path specified by the ``NETRC`` environment variable.
* Authorization headers will be removed if you get redirected off-host.
* Proxy-Authorization headers will be overridden by proxy credentials provided in the URL.
* Content-Length headers will be overridden when we can determine the length of the content.

Furthermore, Niquests does not change its behavior based on which custom
headers are specified. The headers are passed into the final request.

All header values must be a string or bytes-like value. Although Unicode values
are permitted, header values should generally be representable in Latin-1.

More complicated POST requests
------------------------------

Typically, you want to send form-encoded data, much like an HTML form.
To do this, simply pass a dictionary to the ``data`` argument. Your
dictionary of data will automatically be form-encoded when the request is made:

.. tab:: 🔂 Sync

    .. code:: python

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = niquests.post('https://httpbingo.org/post', data=payload)
        print(r.json()['form'])  # {'key1': ['value1'], 'key2': ['value2']}

.. tab:: 🔀 Async

    .. code:: python

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = await niquests.apost('https://httpbingo.org/post', data=payload)
        print(r.json()['form'])  # {'key1': ['value1'], 'key2': ['value2']}

The ``data`` argument can also have multiple values for each key. This can be
done by making ``data`` either a list of tuples or a dictionary with lists
as values. This is particularly useful when the form has multiple elements that
use the same key:

.. tab:: 🔂 Sync

    .. code:: python

        payload_tuples = [('key1', 'value1'), ('key1', 'value2')]
        r1 = niquests.post('https://httpbingo.org/post', data=payload_tuples)
        payload_dict = {'key1': ['value1', 'value2']}
        r2 = niquests.post('https://httpbingo.org/post', data=payload_dict)
        assert r1.json()['form'] == r2.json()['form']

.. tab:: 🔀 Async

    .. code:: python

        payload_tuples = [('key1', 'value1'), ('key1', 'value2')]
        r1 = await niquests.apost('https://httpbingo.org/post', data=payload_tuples)
        payload_dict = {'key1': ['value1', 'value2']}
        r2 = await niquests.apost('https://httpbingo.org/post', data=payload_dict)
        assert r1.json()['form'] == r2.json()['form']

There are times that you may want to send data that is not form-encoded. If
you pass in a string instead of a dictionary, that data will be posted directly.

For example, to encode JSON manually:

.. tab:: 🔂 Sync

    .. code:: python

        import json

        url = 'https://httpbingo.org/post'
        payload = {'some': 'data'}
        r = niquests.post(url, data=json.dumps(payload))

.. tab:: 🔀 Async

    .. code:: python

        import json

        url = 'https://httpbingo.org/post'
        payload = {'some': 'data'}
        r = await niquests.apost(url, data=json.dumps(payload))

The code above does not add a ``Content-Type: application/json`` header.

If you need that header set and do not want to encode the dictionary yourself,
you can pass the object directly using the ``json`` parameter, and it will be
encoded automatically:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.post(url, json=payload)

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.apost(url, json=payload)

The ``json`` parameter is ignored if non-empty ``data`` or ``files`` is passed.

Custom JSON serialization
~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``json_encoder`` to customize request-side JSON serialization. The encoder
is synchronous, even with async APIs, and must return :class:`str` or :class:`bytes`. For
example, `msgspec <https://jcristharif.com/msgspec/>`_ can serialize supported
objects directly to bytes:

.. tab:: 🔂 Sync

    .. code:: python

        import msgspec
        import niquests

        class User(msgspec.Struct):
            name: str
            active: bool

        payload = User(name="Alice", active=True)
        encoder = msgspec.json.encode
        url = "https://httpbingo.org/post"
        r = niquests.post(url, json=payload, json_encoder=encoder)

        with niquests.Session(json_encoder=encoder) as session:
            r = session.post(url, json=payload)

.. tab:: 🔀 Async

    .. code:: python

        import msgspec
        import niquests

        class User(msgspec.Struct):
            name: str
            active: bool

        payload = User(name="Alice", active=True)
        encoder = msgspec.json.encode
        url = "https://httpbingo.org/post"
        r = await niquests.apost(url, json=payload, json_encoder=encoder)

        async with niquests.AsyncSession(json_encoder=encoder) as session:
            r = await session.post(url, json=payload)

Top-level calls create a temporary session, so ``json_encoder`` can be passed directly
to :func:`post() <niquests.post>`, :func:`query() <niquests.query>`,
:func:`apost() <niquests.apost>`, or :func:`aquery() <niquests.aquery>`. A session-level
encoder applies to every request made through that session.

POST multipart form data without a file
---------------------------------------

Since Niquests 3.1.2, you can override the default
``application/x-www-form-urlencoded`` encoding and submit multipart form data
without a file:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.post(
            url, data=payload, headers={'Content-Type': 'multipart/form-data'}
        )

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.apost(
            url, data=payload, headers={'Content-Type': 'multipart/form-data'}
        )

.. note:: You can specify a boundary in the header value. Niquests reuses that
   boundary; otherwise, it generates one.

POST a multipart-encoded file
-----------------------------

Niquests makes it simple to upload multipart-encoded files:

.. tab:: 🔂 Sync

    .. code:: python

        with open('report.xls', 'rb') as report:
            r = niquests.post(url, files={'file': report})

.. tab:: 🔀 Async

    .. code:: python

        with open('report.xls', 'rb') as report:
            r = await niquests.apost(url, files={'file': report})

    .. warning:: Opening a local file is blocking. Use an async file library
       when blocking file I/O is unsuitable for your application.

You can set the filename, content type, and headers explicitly:

.. tab:: 🔂 Sync

    .. code:: python

        with open('report.xls', 'rb') as report:
            files = {
                'file': (
                    'report.xls', report, 'application/vnd.ms-excel', {'Expires': '0'}
                )
            }
            r = niquests.post(url, files=files)

.. tab:: 🔀 Async

    .. code:: python

        with open('report.xls', 'rb') as report:
            files = {
                'file': (
                    'report.xls', report, 'application/vnd.ms-excel', {'Expires': '0'}
                )
            }
            r = await niquests.apost(url, files=files)

You can also send strings as files:

.. tab:: 🔂 Sync

    .. code:: python

        files = {'file': ('report.csv', 'some,data,to,send\nanother,row,to,send\n')}
        r = niquests.post(url, files=files)

.. tab:: 🔀 Async

    .. code:: python

        files = {'file': ('report.csv', 'some,data,to,send\nanother,row,to,send\n')}
        r = await niquests.apost(url, files=files)

In the event you are posting a very large file as a ``multipart/form-data``
request, you may want to stream the request. By default, Niquests does not
provide a multipart streaming encoder, but a separate package does:
``requests-toolbelt``. You should read `the toolbelt's documentation
<https://toolbelt.readthedocs.io>`_ for more details about how to use it.

For information about sending multiple files in one request, see the :ref:`advanced <advanced>`
section.


Response status codes
---------------------

We can check the response status code::

    >>> r = niquests.get('https://httpbingo.org/get')
    >>> r.status_code
    200

Niquests also comes with a built-in status code lookup object for easy
reference::

    >>> r.status_code == niquests.codes.ok
    True

If a request returns a 4xx client error or 5xx server error response, we can
raise an exception with
:meth:`Response.raise_for_status() <niquests.Response.raise_for_status>`::

    >>> bad_r = niquests.get('https://httpbingo.org/status/404')
    >>> bad_r.status_code
    404

    >>> try:
    ...     bad_r.raise_for_status()
    ... except niquests.exceptions.HTTPError:
    ...     print('The response was unsuccessful')
    The response was unsuccessful

Because the :attr:`~niquests.Response.status_code` for ``r`` is ``200``,
:meth:`~niquests.Response.raise_for_status` returns
the response itself::

    >>> r.raise_for_status() is r
    True

All is well.


Response headers
----------------

We can view the server's response headers through a dictionary-like object::

    >>> r.headers
    {
        'content-encoding': 'gzip',
        'transfer-encoding': 'chunked',
        'connection': 'close',
        'server': 'nginx/1.0.4',
        'x-runtime': '148ms',
        'etag': '"e1ca502697e5c9317743dc078f67693f"',
        'content-type': 'application/json; charset=utf-8'
    }

The dictionary is special: it is designed for HTTP fields. According to
:rfc:`9110`, HTTP field names are case-insensitive.

So, we can access the headers using any capitalization we want:

.. container:: termy

   .. code-block:: pycon

      >>> r.headers['Content-Type']
      'application/json; charset=utf-8'
      >>> r.headers.get('content-type')
      'application/json; charset=utf-8'

The server can send some fields multiple times with different values. Niquests
combines fields whose grammar permits comma-separated values so they can be
represented in one mapping. Fields such as ``Set-Cookie``, which cannot be
safely combined this way, are handled separately by the underlying response and
cookie APIs.

In most cases, you may want to access a specific structured field quickly.
The :attr:`~niquests.Response.oheaders` property exposes parsed headers as objects:

.. container:: termy

   .. code-block:: pycon

      >>> r.oheaders.content_type.charset
      'utf-8'
      >>> r.oheaders.report_to.max_age
      '604800'
      >>> str(r.oheaders.date)
      'Mon, 02 Oct 2023 05:34:48 GMT'
      >>> from kiss_headers import get_polymorphic, Date
      >>> h = get_polymorphic(r.oheaders.date, Date)
      >>> repr(h.get_datetime())
      datetime.datetime(2023, 10, 2, 5, 39, 46, tzinfo=datetime.timezone.utc)

To explore possibilities, visit the ``kiss-headers`` documentation at https://jawah.github.io/kiss-headers/

Cookies
-------

If a response contains cookies, you can quickly access them:

.. container:: termy

   .. code-block:: pycon

      >>> url = 'https://httpbingo.org/cookies/set?example_cookie_name=example_cookie_value'
      >>> r = niquests.get(url, allow_redirects=False)

      >>> r.cookies['example_cookie_name']
      'example_cookie_value'

To send your own cookies to the server, you can use the ``cookies``
parameter:

.. container:: termy

   .. code-block:: pycon

      >>> url = 'https://httpbingo.org/cookies'
      >>> cookies = dict(cookies_are='working')

      >>> r = niquests.get(url, cookies=cookies)
      >>> r.json()['cookies']
      {'cookies_are': 'working'}

Cookies are returned in a :class:`~niquests.cookies.RequestsCookieJar`,
which acts like a dictionary but also offers a more complete interface,
suitable for use over multiple domains or paths. Cookie jars can
also be passed in to requests:

.. container:: termy

   .. code-block:: pycon

      >>> jar = niquests.cookies.RequestsCookieJar()
      >>> jar.set('tasty_cookie', 'yum', domain='httpbingo.org', path='/cookies')
      >>> jar.set('gross_cookie', 'blech', domain='httpbingo.org', path='/elsewhere')
      >>> url = 'https://httpbingo.org/cookies'
      >>> r = niquests.get(url, cookies=jar)
      >>> r.json()['cookies']
      {'tasty_cookie': 'yum'}

The same response and request cookie APIs are available asynchronously:

.. code:: python

    r = await niquests.aget(url, cookies=cookies)
    print(r.cookies)

.. note::

    :attr:`Response.cookies <niquests.Response.cookies>`,
    :attr:`Session.cookies <niquests.Session.cookies>` and
    :attr:`AsyncSession.cookies <niquests.AsyncSession.cookies>` are always typed as
    :class:`~niquests.cookies.RequestsCookieJar`. This means you can use them directly as a mapping
    (e.g. ``session.cookies.set(...)`` or ``response.cookies['name']``) without first asserting or
    casting the type, which static type checkers like mypy used to require.

    This is **not** a runtime-breaking change. Any
    :class:`~http.cookiejar.CookieJar` (or plain mapping) you *pass in* is still
    accepted: a plain :class:`~http.cookiejar.CookieJar` is silently coerced to a
    :class:`~niquests.cookies.RequestsCookieJar`, while a custom subclass (such as
    :class:`~http.cookiejar.MozillaCookieJar` and
    other file-backed jars) is left untouched at the request level so it keeps its behavior.

    The only trade-off is that *assigning* a non-:class:`~niquests.cookies.RequestsCookieJar` jar directly to the attribute,
    for instance::

        session.cookies = MozillaCookieJar("cookies.txt")  # type: ignore[assignment]

    will now be flagged by type checkers. The assignment keeps working at runtime; add a
    ``# type: ignore[assignment]`` (or a :func:`~typing.cast`) if you rely on that pattern.

By default, sessions merge cookies received through ``Set-Cookie`` into their
cookie jar. Set ``allow_incoming_cookies=False`` to prevent that merge. Response
cookies remain available, and cookies you set explicitly are still sent:

.. tab:: 🔂 Sync

    .. code:: python

        with niquests.Session(allow_incoming_cookies=False) as session:
            session.cookies.set('outgoing', 'yes')
            r = session.get('https://httpbingo.org/cookies/set?incoming=no')
            assert 'incoming' not in session.cookies

.. tab:: 🔀 Async

    .. code:: python

        async with niquests.AsyncSession(allow_incoming_cookies=False) as session:
            session.cookies.set('outgoing', 'yes')
            r = await session.get('https://httpbingo.org/cookies/set?incoming=no')
            assert 'incoming' not in session.cookies

Redirection and history
-----------------------

By default, Niquests follows redirects for all methods except HEAD.

We can use the :attr:`~niquests.Response.history` property of the response object to track redirects.

The :attr:`Response.history <niquests.Response.history>` list contains the
:class:`Response <niquests.Response>` objects that were created in order to
complete the request. The list is sorted from the oldest to the most recent
response.

For example, GitHub redirects all HTTP requests to HTTPS:

.. container:: termy

   .. code-block:: pycon

      >>> r = niquests.get('http://github.com/')
      >>> r.url
      'https://github.com/'
      >>> r.status_code
      200
      >>> r.history
      [<Response HTTP/2 [301]>]

If you're using GET, OPTIONS, POST, PUT, PATCH, DELETE, or QUERY, you can disable
redirection handling with the ``allow_redirects`` parameter:

.. container:: termy

   .. code-block:: pycon

      >>> r = niquests.get('http://github.com/', allow_redirects=False)
      >>> r.status_code
      301
      >>> r.history
      []

If you're using HEAD, you can enable redirection as well:

.. container:: termy

   .. code-block:: pycon

      >>> r = niquests.head('http://github.com/', allow_redirects=True)
      >>> r.url
      'https://github.com/'
      >>> r.history
      [<Response HTTP/2 [301]>]

The redirect controls and :attr:`~niquests.Response.history` property are identical in async code:

.. code:: python

    r = await niquests.aget('http://github.com/', allow_redirects=False)
    assert r.status_code == 301
    assert r.history == []

    r = await niquests.ahead('http://github.com/', allow_redirects=True)
    assert r.url == 'https://github.com/'
    assert len(r.history) == 1

Timeouts
--------

You can limit how long Niquests waits during network operations with the
``timeout`` parameter. Nearly all production requests should specify a timeout:

.. tab:: 🔂 Sync

    .. code:: python

        try:
            niquests.get('https://github.com/', timeout=0.001)
        except niquests.exceptions.Timeout:
            print('The request timed out')

.. tab:: 🔀 Async

    .. code:: python

        try:
            await niquests.aget('https://github.com/', timeout=0.001)
        except niquests.exceptions.Timeout:
            print('The request timed out')


.. note::

    A scalar ``timeout`` applies to socket connection and read operations; it is
    not a wall-clock limit on the entire response download. A read timeout is
    raised when no response bytes arrive on the socket within that interval.
    You can also pass a ``(connect, read)`` tuple. Top-level GET, HEAD, and
    OPTIONS calls default to 30 seconds; write-oriented methods, including
    QUERY, default to 120 seconds. A session's ``timeout=`` value supplies its
    default when individual session requests omit one.

.. warning::

    Connection timeout behavior can be surprising when a host resolves to
    multiple addresses. Connection attempts may apply the timeout to each
    address in turn, so the elapsed wall-clock time can exceed the configured
    value. For example, two unreachable addresses can take roughly twice the
    connection timeout.

.. tip::

    Set ``happy_eyeballs=True`` when constructing your :class:`~niquests.Session` to try all endpoints simultaneously.
    This can reduce delays caused by unreachable addresses.

.. warning::

    Python's synchronous system resolver cannot always enforce this timeout if
    system DNS is unresponsive. This limitation does not apply to async mode.
    To avoid it, configure a custom resolver with ``resolver=``; see
    `DNS Resolution`_ below.

Errors and exceptions
---------------------

In the event of a network problem, such as a DNS failure or refused connection,
Niquests will raise a :exc:`~niquests.exceptions.ConnectionError` exception.

:meth:`Response.raise_for_status() <niquests.Response.raise_for_status>` will
raise an :exc:`~niquests.exceptions.HTTPError` if the HTTP request
returned an unsuccessful status code.

If a request times out, a :exc:`~niquests.exceptions.Timeout` exception is
raised.

If a request exceeds the configured maximum number of redirects, a
:exc:`~niquests.exceptions.TooManyRedirects` exception is raised.

All exceptions that Niquests explicitly raises inherit from
:exc:`niquests.exceptions.RequestException`.

HTTP/3 over QUIC
----------------

Niquests relies on urllib3.future and the semi-optional ``qh3`` package for HTTP/3.
If ``qh3`` is not installed, HTTP/3 and QUIC are unavailable, but HTTP/1.1 and
HTTP/2 continue to work. Installing ``qh3`` may require a compilation toolchain.

Run ``python -m niquests.help`` to check whether the installed dependencies
support HTTP/3. You can inspect the protocol negotiated for a response:

.. tab:: 🔂 Sync

    .. code:: python

        r = niquests.get('https://1.1.1.1')
        print(r.http_version)

.. tab:: 🔀 Async

    .. code:: python

        r = await niquests.aget('https://1.1.1.1')
        print(r.http_version)

The underlying library understands the ``Alt-Svc`` header and looks for an
``h3`` alternative service. Once a valid service is discovered, Niquests can
open a QUIC connection and caches that information in memory. Negotiation
depends on the peer, DNS and ``Alt-Svc`` information, cached state, network
conditions, and installed dependencies. Repeated calls do not guarantee a
particular HTTP/2-to-HTTP/3 sequence.

.. note:: With urllib3.future 2.4 or later, Niquests can negotiate HTTP/3 without
   a preceding TCP connection when the peer advertises HTTP/3 in an HTTPS DNS
   record.

Lazy responses and manual scheduling
------------------------------------

HTTP/2 and HTTP/3 multiplexing is automatic in Niquests and does not require
this option. The historically named ``multiplexed=True`` option instead enables
manual response scheduling.

In this mode, each request is submitted immediately, but its request method
returns a lazy, promise-backed response before waiting for the exchange to
complete. This lets you submit several requests before resolving any of their
responses.

When the peer supports HTTP/2 or HTTP/3, the outstanding exchanges can progress
concurrently as independent streams on the same connection. Leaving one
response unresolved does not prevent later requests from using that connection.

To benefit from this mode, submit multiple requests before accessing response
data. Resolve the resulting promises explicitly with
:meth:`Session.gather() <niquests.Session.gather>` or
through the other resolution mechanisms described below.

.. note::

   The parameter name is historical. ``multiplexed=True`` does not enable
   HTTP/2 or HTTP/3, and it does not change protocol negotiation. It enables
   lazy responses and gives the caller control over response resolution.

Submit requests
~~~~~~~~~~~~~~~

Request methods return public :class:`~niquests.Response` objects whose
:attr:`~niquests.Response.lazy` property is initially ``True``. Internally, each lazy response is
backed by a response promise.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session
        with Session(multiplexed=True) as s:
            responses = [
                s.get("https://httpbingo.org/delay/3"),
                s.get("https://httpbingo.org/delay/1"),
            ]
            assert all(response.lazy for response in responses)

            s.gather()  # Resolve pending responses before closing the session.

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession
        async with AsyncSession(multiplexed=True) as s:
            responses = [
                await s.get("https://httpbingo.org/delay/3"),
                await s.get("https://httpbingo.org/delay/1"),
            ]
            assert all(response.lazy for response in responses)

            await s.gather()  # Resolve pending responses before closing the session.

The final :meth:`~niquests.Session.gather` calls above are included for deterministic cleanup. The
following sections show how to choose which responses to resolve.

Resolve all responses
~~~~~~~~~~~~~~~~~~~~~

Calling :meth:`~niquests.Session.gather` without response arguments resolves every response pending
on the session:

.. tab:: 🔂 Sync

    .. code:: python

        s.gather()

.. tab:: 🔀 Async

    .. code:: python

        await s.gather()

After resolution, :attr:`response.lazy <niquests.Response.lazy>` is ``False`` and response attributes, body
methods, and extension APIs are available normally.

Resolve selected responses
~~~~~~~~~~~~~~~~~~~~~~~~~~

Pass one or more lazy responses to :meth:`~niquests.Session.gather` to resolve only those promises:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session(multiplexed=True) as s:
            responses = [
                s.get("https://httpbingo.org/delay/3"),
                s.get("https://httpbingo.org/delay/1"),
            ]
            s.gather(responses[0])
            print(responses[0].status_code)
            assert responses[1].lazy is True

            s.gather(responses[1])

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession(multiplexed=True) as s:
            responses = [
                await s.get("https://httpbingo.org/delay/3"),
                await s.get("https://httpbingo.org/delay/1"),
            ]
            await s.gather(responses[0])
            print(responses[0].status_code)
            assert responses[1].lazy is True

            await s.gather(responses[1])

This allows application code to choose the order in which promise-backed
responses are resolved.

Implicit resolution in synchronous code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In synchronous code, directly accessing response data implicitly resolves that
response:

.. code:: python

    with Session(multiplexed=True) as s:
        response = s.get("https://httpbingo.org/delay/1")
        print(response.status_code)  # Resolves this response first.

This implicit behavior is intentionally unavailable for non-awaitable
attributes on a lazy :class:`~niquests.AsyncResponse`, because blocking there
would stall the event loop. Resolve it explicitly with ``await s.gather(...)``.

Scheduling limits with ``max_fetch``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Both session types expose
:meth:`gather(*responses, max_fetch=None) <niquests.Session.gather>`.
``max_fetch`` limits how many available promises each mounted adapter resolves
during that call.

Here are some possible invocations:

.. tab:: 🔂 Sync

    .. code:: python

        s.gather()  # Resolve all pending responses.
        s.gather(resp)  # Resolve only resp.
        s.gather(max_fetch=2)  # Resolve up to two available responses per adapter.
        s.gather(resp_a, resp_b, resp_c)  # Resolve these three responses.
        s.gather(resp_a, resp_b, resp_c, max_fetch=1)  # Resolve one available response per adapter.

.. tab:: 🔀 Async

    .. code:: python

        await s.gather()  # Resolve all pending responses.
        await s.gather(resp)  # Resolve only resp.
        await s.gather(max_fetch=2)  # Resolve up to two available responses per adapter.
        await s.gather(resp_a, resp_b, resp_c)  # Resolve these three responses.
        await s.gather(resp_a, resp_b, resp_c, max_fetch=1)  # Resolve one available response per adapter.

Async session
-------------

Niquests provides :class:`~niquests.AsyncSession` for awaitable HTTP requests.
Its request methods mirror :class:`~niquests.Session` and return coroutines.

Here is a basic example::

    import asyncio
    from niquests import AsyncSession, Response

    async def main() -> None:
        async with AsyncSession() as s:
            tasks = [s.get("https://httpbingo.org/delay/1") for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            print(responses)

    if __name__ == "__main__":
        asyncio.run(main())


.. warning:: Niquests currently supports only :mod:`asyncio` as its async backend.

.. note:: Top-level async shortcuts are available with an ``a`` prefix, including
   :func:`aget() <niquests.aget>`, :func:`apost() <niquests.apost>`,
   :func:`aput() <niquests.aput>`, :func:`apatch() <niquests.apatch>`,
   :func:`adelete() <niquests.adelete>`, :func:`aoptions() <niquests.aoptions>`,
   :func:`ahead() <niquests.ahead>`, :func:`aquery() <niquests.aquery>`, and
   :func:`arequest() <niquests.arequest>`. Each call uses
   a temporary :class:`~niquests.AsyncSession`; use your own session to reuse
   connections.

Async lazy responses and manual scheduling
------------------------------------------

``AsyncSession(multiplexed=True)`` uses the same manual response scheduling
described above. It does not enable HTTP/2 or HTTP/3 multiplexing; protocol
negotiation remains automatic.

Each awaited request method submits its request and returns a lazy,
promise-backed response without waiting for that exchange to finish. Submit
several requests before resolving them so HTTP/2 or HTTP/3 streams can progress
concurrently on the underlying connection. Resolve the promises explicitly with
``await session.gather()``.

Look at this basic sample::

    import asyncio
    from niquests import AsyncSession

    async def main() -> None:
        async with AsyncSession(multiplexed=True) as s:
            responses = [
                await s.get("https://httpbingo.org/delay/1") for _ in range(10)
            ]
            assert all(response.lazy for response in responses)

            await s.gather()
            assert all(response.lazy is False for response in responses)
            print(responses)

    if __name__ == "__main__":
        asyncio.run(main())


Unlike synchronous lazy responses, an asynchronous lazy response cannot resolve
itself while a non-awaitable attribute is being accessed, because doing so would
block the event loop. Gather it explicitly before that access.

.. warning:: Combining :class:`~niquests.AsyncSession` with ``multiplexed=True``
   and ``stream=True`` produces a lazy :class:`~niquests.AsyncResponse`. Call
   ``await session.gather()`` before directly accessing its non-awaitable
   attributes or methods.

AsyncResponse for streams
-------------------------

Delaying the content consumption in an async context can be easily achieved using::

    import niquests
    import asyncio

    async def main() -> None:

        async with niquests.AsyncSession() as s:
            r = await s.get("https://httpbingo.org/get", stream=True)

            async for chunk in await r.iter_content(16):
                print(chunk)

    if __name__ == "__main__":

        asyncio.run(main())

Or use :meth:`~niquests.AsyncResponse.iter_lines`. It is an async generator, so iterate over it directly
without ``await``::

    import niquests
    import asyncio

    async def main() -> None:

        async with niquests.AsyncSession() as s:
            r = await s.get("https://httpbingo.org/get", stream=True)

            async for line in r.iter_lines():
                print(line)

    if __name__ == "__main__":
        asyncio.run(main())

Or simply by doing::

    import niquests
    import asyncio

    async def main() -> None:

        async with niquests.AsyncSession() as s:
            r = await s.get("https://httpbingo.org/get", stream=True)
            payload = await r.json()

    if __name__ == "__main__":

        asyncio.run(main())

When you specify ``stream=True`` with :class:`~niquests.AsyncSession`, the
returned object is an :class:`~niquests.AsyncResponse`. Its
:meth:`~niquests.AsyncResponse.iter_content` and
:meth:`~niquests.AsyncResponse.iter_raw` methods are awaitable and return async iterators, so use
``async for chunk in await response.iter_content()``. In contrast,
:meth:`~niquests.AsyncResponse.iter_lines` is an async generator and is used as
``async for line in response.iter_lines()`` without ``await``. The
:attr:`~niquests.AsyncResponse.content`, :meth:`~niquests.AsyncResponse.json`,
:attr:`~niquests.AsyncResponse.text`, and :meth:`~niquests.AsyncResponse.close`
interfaces are also awaitable.

When enabling multiplexing in an async context, call ``await s.gather()`` before
direct access to non-awaitable response interfaces.

Here is a basic example of how you would do it::

    import niquests
    import asyncio

    async def main() -> None:

        responses = []

        async with niquests.AsyncSession(multiplexed=True) as s:
            responses.append(
                await s.get("https://httpbingo.org/get", stream=True)
            )
            responses.append(
                await s.get("https://httpbingo.org/get", stream=True)
            )

            print(responses)

            await s.gather()

            print(responses)

            for response in responses:
                async for chunk in await response.iter_content(16):
                    print(chunk)


    if __name__ == "__main__":

        asyncio.run(main())

.. warning:: Accessing a non-awaitable attribute or method of a lazy
   :class:`~niquests.AsyncResponse` without first calling ``await s.gather()``
   raises an error.

Scale your Session / pool
-------------------------

By default, Niquests retains up to 10 origin pools and configures each pool with
a capacity of 10 connections. You can increase or decrease these values.

Set the following parameters in a session constructor:

``Session(pool_connections=10, pool_maxsize=10)``

- ``pool_connections`` is the number of origin connection pools retained in the cache.
- ``pool_maxsize`` is the configured connection capacity of each origin pool.

.. tip:: HTTP/2 and HTTP/3 can carry many concurrent streams over one
   connection, subject to the peer's advertised stream limit.

.. note:: These settings are most useful for multithreaded or async applications.

Pool connections
~~~~~~~~~~~~~~~~

After requests to three distinct origins, ``pool_connections=2`` retains the two
most recently used origin pools, for ``host-b.tld`` and ``host-c.tld``. The idle
pool for ``host-a.tld`` is evicted from the cache.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        with niquests.Session(pool_connections=2) as s:
            s.get("https://host-a.tld/some")
            s.get("https://host-b.tld/some")
            s.get("https://host-c.tld/some")

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        async with niquests.AsyncSession(pool_connections=2) as s:
            await s.get("https://host-a.tld/some")
            await s.get("https://host-b.tld/some")
            await s.get("https://host-c.tld/some")

.. attention::

    For backward compatibility, this cache size applies per mounted adapter.
    The default HTTP and HTTPS adapters each retain up to two origin pools when
    ``pool_connections=2``, so pools for up to four origins may be retained
    across both schemes.

Pool maxsize
~~~~~~~~~~~~

Setting ``pool_maxsize=2`` configures a capacity of two connections for the
``host-a.tld`` origin pool. This setting matters primarily in concurrent async
or threaded environments.

DNS resolution
--------------

Niquests has built-in support for DNS over HTTPS, DNS over TLS, DNS over UDP,
and DNS over QUIC. Encrypted resolvers use the configured trust store for
certificate validation.

This feature uses the native urllib3.future implementation.
The security properties of a custom resolver depend on the chosen transport and
provider. DNSSEC validation is available when supported and enabled by the
resolver implementation and provider.

Specify your own resolver
~~~~~~~~~~~~~~~~~~~~~~~~~

To specify a resolver, use a :class:`~niquests.Session` or
:class:`~niquests.AsyncSession`. Each session can have a different resolver.
This example uses Google Public DNS over HTTPS:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session(resolver="doh+google://") as s:
            resp = s.get("https://httpbingo.org/get")

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession(resolver="doh+google://") as s:
            resp = await s.get("https://httpbingo.org/get")

Here, ``httpbingo.org`` is resolved using the configured provider.

.. note:: By default, Niquests uses the system resolver.

The ``resolver`` argument also accepts public urllib3.future resolver
configuration objects. Use
:class:`niquests.packages.urllib3.ResolverDescription <urllib3.contrib.resolver.factories.ResolverDescription>`
with :class:`~niquests.Session` and
:class:`~urllib3.contrib.resolver._async.factories.AsyncResolverDescription` with
:class:`~niquests.AsyncSession` when you need to configure resolver fields
programmatically. See :ref:`advanced <advanced>` for detailed resolver and
:class:`~niquests.TLSConfiguration` examples. :class:`~niquests.TLSConfiguration` can be passed
as ``tls_configuration=`` to top-level sync/async calls or either session type
to select a TLS backend, protocol versions, ciphers, or hostname policy.

Use multiple resolvers
~~~~~~~~~~~~~~~~~~~~~~

You may specify a list of resolvers to be tested in the listed order.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session(resolver=["doh+google://", "doh://cloudflare-dns.com"]) as s:
            resp = s.get("https://httpbingo.org/get")

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession(resolver=["doh+google://", "doh://cloudflare-dns.com"]) as s:
            resp = await s.get("https://httpbingo.org/get")

The second entry, ``doh://cloudflare-dns.com``, is tested only if
``doh+google://`` fails to provide a usable answer.

.. note:: In a multithreaded context, both resolvers may be used to improve
   performance.

Supported DNS URLs
~~~~~~~~~~~~~~~~~~

Niquests supports a wide range of DNS protocols. Here are a few examples::

    "doh+google://"  # Shortcut for Google DNS over HTTPS.
    "dot+google://"  # Shortcut for Google DNS over TLS.
    "doh+cloudflare://"  # Shortcut for Cloudflare DNS over HTTPS.
    "doq+adguard://"  # Shortcut for AdGuard DNS over QUIC.
    "dou://1.1.1.1"  # DNS over UDP.
    "dou://1.1.1.1:8853"  # DNS over UDP on port 8853.
    "doh://my-resolver.tld"  # DNS over HTTPS with a custom server.

.. note:: Learn more by looking at the **urllib3.future** documentation: https://urllib3future.readthedocs.io/en/latest/advanced-usage.html#using-a-custom-dns-resolver

Set DNS via the environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can set the ``NIQUESTS_DNS_URL`` environment variable to the desired
resolver. It is used by every session **that does not explicitly specify a
resolver.**

Example::

    export NIQUESTS_DNS_URL="doh://google.dns"

Disable DNS certificate verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add ``verify=false`` to the DNS URL. Disabling certificate verification is
unsafe and should be limited to controlled testing environments.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session(resolver="doh+google://default/?verify=false") as s:
            resp = s.get("https://httpbingo.org/get")

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession(resolver="doh+google://default/?verify=false") as s:
            resp = await s.get("https://httpbingo.org/get")

.. warning:: Doing a ``s.get("https://httpbingo.org/get", verify=False)`` does not impact the resolver.

Timeouts
~~~~~~~~

You may set a specific timeout for domain name resolution by appending ``?timeout=1`` to the resolver configuration.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session(resolver="doh+google://default/?timeout=1") as s:
            resp = s.get("https://httpbingo.org/get")

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession(resolver="doh+google://default/?timeout=1") as s:
            resp = await s.get("https://httpbingo.org/get")

This prevents an individual DNS operation from waiting longer than one second.

Happy Eyeballs
--------------

.. versionadded:: 3.5.5

The underlying urllib3.future library provides Happy Eyeballs behind one option.

Happy Eyeballs (also called Fast Fallback) is an algorithm published by the IETF that makes dual-stack applications
(those that understand both IPv4 and IPv6) more responsive to users by attempting to connect using both IPv4 and IPv6
at the same time (preferring IPv6), thus minimizing common problems experienced by users with imperfect IPv6 connections or setups.

The name "Happy Eyeballs" uses "eyeball" to describe endpoints that represent
human Internet users, as opposed to servers.

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        with niquests.Session(happy_eyeballs=True) as s:
            ...

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        async with niquests.AsyncSession(happy_eyeballs=True) as s:
            ...

A single ``happy_eyeballs=True`` option enables the algorithm.

.. note:: This also applies when a server yields multiple IPv4 addresses but no
   IPv6 addresses. Niquests connects concurrently to the presented addresses
   and uses the fastest endpoint.

.. note:: You can pass an integer to change the number of concurrent connections
   tested. See https://urllib3future.readthedocs.io/en/latest/advanced-usage.html#happy-eyeballs.

OCSP requests for certificate revocation checks also use the configured Happy
Eyeballs setting.

.. warning:: This feature is disabled by default. It may become the default in a
   future major release.

WebSockets
----------

.. versionadded:: 3.9
   Requires the WebSocket extra: ``pip install niquests[ws]``.

WebSockets are a vital part of the web ecosystem alongside HTTP. Niquests
provides an integrated interface to reduce the friction of connecting to a
WebSocket server for the first time.

Quick start
~~~~~~~~~~~

The following example interacts with a basic, well-known echo server.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session() as s:
            resp = s.get(
                "wss://echo.websocket.org",
            )

            print(resp.status_code)  # 101 Switching Protocols

            print(resp.extension.next_payload())  # Read the next server message.

            resp.extension.send_payload("Hello World")

            print(resp.extension.next_payload() == "Hello World")  # True

            resp.extension.close()

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession
        import asyncio

        async def main() -> None:
            async with AsyncSession() as s:
                resp = await s.get("wss://echo.websocket.org")

                # ...

                print(await resp.extension.next_payload())  # unpack the next message from server

                await resp.extension.send_payload("Hello World")

                print((await resp.extension.next_payload()) == "Hello World")  # output True!

                await resp.extension.close()

        asyncio.run(main())

.. warning:: Without the extra installed, an exception indicates that the
   scheme is unsupported.

.. note:: Requests historically accepted only ``http://`` and ``https://``.
   Niquests also accepts ``wss://`` for WebSocket Secure and ``ws://`` for
   plaintext WebSocket.

.. warning:: If the server rejects the WebSocket upgrade,
   :attr:`resp.extension <niquests.Response.extension>` is
   ``None``. Check it before using extension methods when rejection is possible.

WebSocket and HTTP/2+
~~~~~~~~~~~~~~~~~~~~~

By default, Niquests negotiates WebSocket over HTTP/1.1. It can also use the
extended CONNECT mechanism from :rfc:`8441` over HTTP/2 or HTTP/3. Few servers
support WebSocket over a multiplexed connection; use a URL such as
``wss+rfc8441://example.com`` to request this mode.

.. warning:: ``echo.websocket.org`` does not support WebSocket over HTTP/2.

Ping and pong
~~~~~~~~~~~~~

Pings sent by a server are answered automatically while Niquests reads from the socket
through
:meth:`~urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.next_payload`.
Niquests does not automatically send pings to
the server.

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session() as s:
            resp = s.get(
                "wss://echo.websocket.org",
            )

            resp.extension.ping()  # Send a ping to the WebSocket server.

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession() as s:
            resp = await s.get(
                "wss://echo.websocket.org",
            )

            await resp.extension.ping()  # Send a ping to the WebSocket server.

You can use the elementary methods provided by Niquests to construct your own logic.

Binary and text messages
~~~~~~~~~~~~~~~~~~~~~~~~

You may use
:meth:`~urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.next_payload` and
:meth:`send_payload(...) <urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.send_payload>`
with :class:`str` or :class:`bytes`.

If :meth:`~urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.next_payload`
returns bytes, the message is binary. If it returns a
string, the message is text.

The same distinction applies to
:meth:`send_payload(...) <urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.send_payload>`:
strings produce text
messages, while bytes produce binary messages.

.. warning:: Niquests does not buffer incomplete messages. It returns each
   received chunk as is.

.. note:: If
   :meth:`~urllib3.contrib.webextensions.ws.WebSocketExtensionFromHTTP.next_payload`
   returns ``None``, the remote peer has closed the
   connection.

Others
~~~~~~

Other features, including proxies, Happy Eyeballs, and thread/task safety, also
apply to WebSocket connections. See the relevant sections for details.

Example with concurrency
~~~~~~~~~~~~~~~~~~~~~~~~

The following example communicates with a WebSocket echo server. It uses a
thread for reads and the main thread for writes.

.. tab:: 🔂 Sync

    .. code:: python

        from __future__ import annotations

        from niquests import Session, Response, ReadTimeout
        from threading import Thread
        from time import sleep


        def pull_message_from_server(my_response: Response) -> None:
            """Read messages here."""
            iteration_counter = 0

            while my_response.extension.closed is False:
                try:
                    # Blocks for at most one second.
                    message = my_response.extension.next_payload()

                    if message is None:  # server just closed the connection. exit.
                        print("received goaway from server")
                        return

                    print(f"received message: '{message}'")
                except ReadTimeout:  # if no message received within 1s
                    pass

                sleep(1)  # let some time for the write part to acquire the lock
                iteration_counter += 1

                # Send a ping every four iterations.
                if iteration_counter % 4 == 0:
                    my_response.extension.ping()
                    print("ping sent")

        if __name__ == "__main__":

            with Session() as s:
                # connect to websocket server "echo.websocket.org" with timeout of 1s (both read and connect)
                resp = s.get("wss://echo.websocket.org", timeout=1)

                if resp.status_code != 101:
                    exit(1)

                t = Thread(target=pull_message_from_server, args=(resp,))
                t.start()

                # Send messages here.
                for i in range(30):
                    to_send = f"Hello World {i}"
                    resp.extension.send_payload(to_send)
                    print(f"sent message: '{to_send}'")
                    sleep(1)  # let some time for the read part to acquire the lock

                # exit gently!
                resp.extension.close()

                # wait for thread proper exit.
                t.join()

                print("program ended!")

    .. warning:: The sleeps give each side an opportunity to acquire the shared
       read/write lock and prevent starvation.

.. tab:: 🔀 Async

    .. code:: python

        import asyncio
        from niquests import AsyncSession, ReadTimeout, Response

        async def read_from_ws(my_response: Response) -> None:
            iteration_counter = 0

            while my_response.extension.closed is False:
                try:
                    # Blocks for at most one second.
                    message = await my_response.extension.next_payload()

                    if message is None:  # server just closed the connection. exit.
                        print("received goaway from server")
                        return

                    print(f"received message: '{message}'")
                except ReadTimeout:  # if no message received within 1s
                    pass

                await asyncio.sleep(1)  # let some time for the write part to acquire the lock
                iteration_counter += 1

                # Send a ping every four iterations.
                if iteration_counter % 4 == 0:
                    await my_response.extension.ping()
                    print("ping sent")

        async def main() -> None:
            async with AsyncSession() as s:
                resp = await s.get("wss://echo.websocket.org", timeout=1)

                print(resp)

                task = asyncio.create_task(read_from_ws(resp))

                for i in range(30):
                    to_send = f"Hello World {i}"
                    await resp.extension.send_payload(to_send)
                    print(f"sent message: '{to_send}'")
                    await asyncio.sleep(1)  # let some time for the read part to acquire the lock

                # exit gently!
                await resp.extension.close()
                await task


        if __name__ == "__main__":
            asyncio.run(main())

.. note:: These examples are intentionally basic. Adjust their settings and
   algorithms to match your requirements.

Server-sent events (SSE)
------------------------

.. versionadded:: 3.11.2

Server-Sent Events, commonly abbreviated SSE, provide a standard way to stream
events continuously from a server to a client in real time.

Starting example
~~~~~~~~~~~~~~~~

The native urllib3.future SSE extension manages a stream of events:

.. tab:: 🔂 Sync

    .. code:: python

        from __future__ import annotations

        import niquests

        if __name__ == "__main__":
            with niquests.Session() as s:
                r = s.post("sse://httpbingo.org/sse")
                print(r.status_code)

                while r.extension.closed is False:
                    event: niquests.ServerSentEvent | None = r.extension.next_payload()
                    print(event)

.. tab:: 🔀 Async

    .. code:: python

        import niquests
        import asyncio

        async def main() -> None:
            async with niquests.AsyncSession() as s:
                r = await s.post("sse://httpbingo.org/sse")

                print(r)  # output: <Response HTTP/2 [200]>

                while r.extension.closed is False:
                    print(await r.extension.next_payload())  # ServerSentEvent(event='ping', data='{"id":0,"timestamp":1732857000473}')

        if __name__ == "__main__":

            asyncio.run(main())

The ``sse://`` scheme indicates the intent to consume an SSE endpoint.

.. note:: ``sse://`` uses ``https://`` underneath. For an unencrypted
   connection, use ``psse://``.

The interface resembles the WebSocket implementation, except that
:meth:`~urllib3.contrib.webextensions.sse.ServerSideEventExtensionFromHTTP.next_payload`
returns a :class:`~urllib3.contrib.webextensions.sse.ServerSentEvent` object by default.

Extracting raw events
~~~~~~~~~~~~~~~~~~~~~

If a server uses custom fields or a nonstandard line format, pass ``raw=True``
to retrieve a string instead of a
:class:`~urllib3.contrib.webextensions.sse.ServerSentEvent` object:

.. tab:: 🔂 Sync

    .. code:: python

        while r.extension.closed is False:
            raw_event = r.extension.next_payload(raw=True)
            if raw_event is None:
                break
            print(raw_event)

.. tab:: 🔀 Async

    .. code:: python

        while r.extension.closed is False:
            raw_event = await r.extension.next_payload(raw=True)
            if raw_event is None:
                break
            print(raw_event)

.. warning:: As with WebSocket,
   :meth:`~urllib3.contrib.webextensions.sse.ServerSideEventExtensionFromHTTP.next_payload`
   may return ``None`` when the
   server terminates the stream.

Interrupt the stream
~~~~~~~~~~~~~~~~~~~~

A server may send events forever. Always close the SSE extension when you stop
consuming it so the remote peer is notified.

For example, ``sse://sse.dev/test`` sends events until the client stops it.

See how to stop cleanly the flow of events:

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        if __name__ == "__main__":
            with niquests.Session() as s:
                r = s.post("sse://sse.dev/test")
                events = []

                while r.extension.closed is False:
                    event = r.extension.next_payload()
                    if event is None:  # The remote peer closed the stream.
                        break

                events.append(event)  # add the event to list

                if len(events) >= 10:  # close ourselves SSE stream & notify remote peer.
                    r.extension.close()

.. tab:: 🔀 Async

    .. code:: python

        import niquests
        import asyncio

        async def main() -> None:
            async with niquests.AsyncSession() as s:
                r = await s.post("sse://sse.dev/test")

                events = []

                while r.extension.closed is False:
                    event = await r.extension.next_payload()

                    if event is None:  # The remote peer closed the stream.
                        break

                    events.append(event)  # add the event to list

                    if len(events) >= 10:  # close ourselves SSE stream & notify remote peer.
                        await r.extension.close()

        if __name__ == "__main__":

            asyncio.run(main())

ServerSentEvent
~~~~~~~~~~~~~~~

.. note::
   :meth:`~urllib3.contrib.webextensions.sse.ServerSideEventExtensionFromHTTP.next_payload`
   returns a :class:`~urllib3.contrib.webextensions.sse.ServerSentEvent` by default, or
   ``None`` when the server terminates the event stream.

This object represents one parsed event and provides these attributes and methods:

- :meth:`payload.json() <urllib3.contrib.webextensions.sse.ServerSentEvent.json>` to deserialize JSON data
- :attr:`payload.id <urllib3.contrib.webextensions.sse.ServerSentEvent.id>` for the event ID
- :attr:`payload.data <urllib3.contrib.webextensions.sse.ServerSentEvent.data>` for the raw message payload
- :attr:`payload.event <urllib3.contrib.webextensions.sse.ServerSentEvent.event>` for the event type, such as ``message`` or ``ping``
- :attr:`payload.retry <urllib3.contrib.webextensions.sse.ServerSentEvent.retry>` for the reconnection time

The full class source is located at https://github.com/jawah/urllib3.future/blob/3d7c5d9446880a8d473b9be4db0bcd419fb32dee/src/urllib3/contrib/webextensions/sse.py#L14

Notes
~~~~~

SSE can use HTTP/1.1, HTTP/2, or HTTP/3. Features such as proxies, Happy
Eyeballs, and hooks remain available.

Unix sockets
------------

.. versionadded:: 3.17.0
.. warning:: Unix domain sockets are available only on Linux and Unix-like
   systems. They support HTTP/1.1 and cleartext HTTP/2 (h2c), not HTTP/3.

Niquests natively supports connecting to services through Unix domain sockets.
This is useful for local services, such as the Docker Engine API, databases, or
any application that exposes an HTTP API over a Unix socket.

Basic usage
~~~~~~~~~~~

To connect via a Unix socket, use the ``http+unix://`` scheme with the URL-encoded socket path:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session() as s:
            # %2F is the URL-encoded forward slash
            response = s.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/version")
            print(response.json())

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession() as s:
            response = await s.get("http+unix://%2Fvar%2Frun%2Fdocker.sock/version")
            print(response.json())

.. tip:: Use the ``base_url`` parameter on a session to avoid repeatedly writing
   ``http+unix://%2Fvar%2Frun%2Fdocker.sock/``.

.. warning:: To use h2c over a Unix socket, disable HTTP/1.1 with
   ``Session(disable_http1=True)``. Few services support this configuration.

URL format
~~~~~~~~~~

The Unix socket URL follows this pattern::

    http+unix://<url-encoded-socket-path>/<api-path>

For example, to access ``/var/run/docker.sock`` with path ``/version``:

- Socket path: ``/var/run/docker.sock``
- URL-encoded: ``%2Fvar%2Frun%2Fdocker.sock``
- Full URL: ``http+unix://%2Fvar%2Frun%2Fdocker.sock/version``

.. tip:: Use ``urllib.parse.quote(path, safe='')`` to URL-encode socket paths programmatically.

Concurrent connections
~~~~~~~~~~~~~~~~~~~~~~

Unix sockets support multiple concurrent connections, just like TCP sockets:

.. tab:: 🔂 Sync

    .. code:: python

        from concurrent.futures import ThreadPoolExecutor
        from niquests import Session

        endpoints = ["/containers/json", "/images/json", "/version", "/info"]
        with Session() as s, ThreadPoolExecutor() as executor:
            responses = list(executor.map(
                lambda endpoint: s.get(
                    f"http+unix://%2Fvar%2Frun%2Fdocker.sock{endpoint}"
                ),
                endpoints,
            ))

.. tab:: 🔀 Async

    .. code:: python

        import asyncio
        from niquests import AsyncSession

        async with AsyncSession() as s:
            endpoints = ["/containers/json", "/images/json", "/version", "/info"]
            responses = await asyncio.gather(*(
                s.get(f"http+unix://%2Fvar%2Frun%2Fdocker.sock{endpoint}")
                for endpoint in endpoints
            ))

WebSocket and SSE
~~~~~~~~~~~~~~~~~

.. versionadded:: 3.18.0

WebSocket and SSE extensions are also available over Unix sockets:

.. tab:: 🔂 Sync

    .. code:: python

        import niquests

        with niquests.Session() as s:
            r = s.get("psse+unix://%2Ftmp%2Fhello.sock/sse")
            while not r.extension.closed:
                print(r.extension.next_payload())

            ws = s.get("ws+unix://%2Ftmp%2Fhello.sock/ws")
            ws.extension.send_payload("Hello")
            print(ws.extension.next_payload())
            ws.extension.close()

.. tab:: 🔀 Async

    .. code:: python

        import niquests

        async with niquests.AsyncSession() as s:
            r = await s.get("psse+unix://%2Ftmp%2Fhello.sock/sse")
            while not r.extension.closed:
                print(await r.extension.next_payload())

            ws = await s.get("ws+unix://%2Ftmp%2Fhello.sock/ws")
            await ws.extension.send_payload("Hello")
            print(await ws.extension.next_payload())
            await ws.extension.close()

The ``psse+unix://`` scheme, rather than ``http+unix://``, tells Niquests to
initialize :attr:`response.extension <niquests.Response.extension>` for SSE.

Use ``psse+unix://`` for SSE and ``ws+unix://`` for WebSocket. See the dedicated
sections above for their interfaces.

.. warning:: ``ws+unix://`` requires you to have the ``ws`` extra installed.

WSGI/ASGI application testing
-----------------------------

.. versionadded:: 3.17.0

Niquests provides built-in adapters for testing WSGI and ASGI applications
directly without starting a server. This is particularly useful for integration
testing.

.. warning:: In-process adapters ignore connection-specific settings such as
   HTTP version toggles, pool sizing, and multiplexing.

ASGI applications (async)
~~~~~~~~~~~~~~~~~~~~~~~~~

Test your FastAPI, Starlette, or other ASGI applications directly:

.. code:: python

    from fastapi import FastAPI, Request

    app = FastAPI()

    @app.get("/hello")
    async def hello(request: Request):
        return {"message": "hello from asgi"}

    @app.api_route("/echo", methods=["GET", "POST"])
    async def echo(request: Request):
        body = await request.body()
        return {"body": body.decode()}

**Basic usage:**

.. code:: python

    import asyncio
    from niquests import AsyncSession

    async def main():
        async with AsyncSession(app=app) as s:
            resp = await s.get("/hello?foo=bar")
            print(resp.status_code)  # 200
            print(resp.json())  # {"message": "hello from asgi"}

    asyncio.run(main())

**Ordinary streaming responses:**

.. code:: python

    async def main():
        async with AsyncSession(app=app) as s:
            resp = await s.post("/echo", data=b"foobar", stream=True)

            body = b""
            async for chunk in await resp.iter_content(6):
                body += chunk

            print(body)

    asyncio.run(main())

The async ASGI adapter exposes ordinary streamed response bodies through
:class:`~niquests.AsyncResponse`, as shown above. This is separate from the
WebSocket and SSE extension protocols below.

**WebSocket and SSE:**

.. versionadded:: 3.18.0

WebSocket and Server-Sent Events work with ASGI applications using the exact same interfaces as the main HTTP part.
Use ``wss://`` (or ``ws://``) for WebSocket and ``sse://`` (or ``psse://``) for SSE, just like you would with a live server.

.. tab:: 🔂 Sync

    .. code:: python

        from fastapi import FastAPI, WebSocket
        from starlette.responses import StreamingResponse

        app = FastAPI()

        @app.websocket("/ws-echo")
        async def ws_echo(websocket: WebSocket):
            await websocket.accept()
            while True:
                data = await websocket.receive_text()
                await websocket.send_text(f"echo: {data}")

        @app.get("/sse-events")
        async def sse_events():
            async def generate():
                for i in range(3):
                    yield f"event: message\ndata: event {i}\n\n"
            return StreamingResponse(generate(), media_type="text/event-stream")

    WebSocket:

    .. code:: python

        from niquests import Session

        with Session(app=app) as s:
            resp = s.get("wss://default/ws-echo")

            resp.extension.send_payload("Hello")
            print(resp.extension.next_payload())  # "echo: Hello"

            resp.extension.close()

    SSE:

    .. code:: python

        from niquests import Session

        with Session(app=app) as s:
            resp = s.get("sse://default/sse-events")

            while not resp.extension.closed:
                event = resp.extension.next_payload()
                if event is None:
                    break
                print(event)  # ServerSentEvent(event='message', data='event 0')

.. tab:: 🔀 Async

    .. code:: python

        import asyncio
        from niquests import AsyncSession

        async def main():
            async with AsyncSession(app=app) as s:
                # WebSocket
                resp = await s.get("wss://default/ws-echo")
                await resp.extension.send_payload("Hello")
                print(await resp.extension.next_payload())  # "echo: Hello"
                await resp.extension.close()

                # SSE
                resp = await s.get("sse://default/sse-events")
                while not resp.extension.closed:
                    event = await resp.extension.next_payload()
                    if event is None:
                        break
                    print(event)

        asyncio.run(main())

.. note:: You can also use an ASGI app with a synchronous session. Ordinary
   ASGI response bodies are buffered in that mode, so ``stream=True`` does not
   provide incremental body delivery. WebSocket and SSE still stream through
   :attr:`response.extension <niquests.Response.extension>` as shown above. The synchronous adapter handles ASGI
   lifespan startup and shutdown events automatically.

WSGI applications (sync)
~~~~~~~~~~~~~~~~~~~~~~~~

Test your Flask, Django, or other WSGI applications:

.. code:: python

    from flask import Flask, request, jsonify

    app = Flask(__name__)

    @app.route("/hello")
    def hello():
        return jsonify({"message": "hello from wsgi"})

    @app.route("/echo", methods=["GET", "POST"])
    def echo():
        return jsonify({"body": request.get_data(as_text=True)})

**Basic usage:**

.. code:: python

    from niquests import Session

    with Session(app=app) as s:
        resp = s.get("/hello?foo=bar")
        print(resp.status_code)  # 200
        print(resp.json())  # {"message": "hello from wsgi"}

**Streaming responses:**

.. code:: python

    with Session(app=app) as s:
        resp = s.post("/echo", data=b"foobar", stream=True)
        print(resp.json())

        for chunk in resp.iter_content(6):
            ...

**Server-Sent Events:**

.. versionadded:: 3.18.0

SSE works with WSGI applications using the same interface as the main HTTP part.

.. code:: python

    from flask import Flask, Response

    app = Flask(__name__)

    @app.route("/sse-events")
    def sse_events():
        def generate():
            for i in range(3):
                yield f"event: message\ndata: event {i}\n\n"
        return Response(generate(), mimetype="text/event-stream")

.. code:: python

    from niquests import Session

    with Session(app=app) as s:
        resp = s.get("sse://default/sse-events")

        while not resp.extension.closed:
            event = resp.extension.next_payload()
            if event is None:
                break
            print(event)  # ServerSentEvent(event='message', data='event 0')

.. warning:: The WSGI adapter is request/response-only and does not support
   WebSocket. Use an ASGI application for WebSocket testing.

Running as a WASI component
---------------------------

.. versionadded:: 3.21.0

WASI is an excellent fit for sandboxed applications, plug-ins, serverless functions,
and edge deployments. A component starts without ambient access to the network or
filesystem: its WIT world declares what it can use, and the host decides which of
those capabilities to grant when it runs the component. The same component can
therefore be deployed under different security policies without changing its Python
code.

.. tip:: WASI can play a key role in deploying agents at scale. A library such
   as `padwan-llm <https://github.com/polarsen-io/padwan-llm>`_ can help build
   agent loops in a constrained WASI runtime using Niquests.

For the most complete Niquests experience, prefer the WASI socket interfaces. Use
Preview 2 sockets for synchronous code and Preview 3 sockets for asynchronous code.
The matching ``wasi:cli/command`` world from the componentize-py source distribution
includes those interfaces.

Install Niquests with the Rustls backend so that HTTPS can run over WASI sockets, then
download the matching componentize-py source archive:

.. code:: console

    $ python -m pip install "niquests[rtls]" "componentize-py==0.25.0"
    $ python -m pip download --no-deps --no-binary=:all: "componentize-py==0.25.0"
    $ python -m tarfile -e componentize_py-0.25.0.tar.gz .

.. note::

    The PyPI wheel installs the ``componentize-py`` executable but does not include
    its WASI WIT definitions. The source archive provides the required ``wit/``
    directory; keep both at the same pinned version.

Choose the execution model for your component:

.. tab:: 🔂 Sync

    Use Preview 2 sockets for a synchronous component:

    .. code:: python

        import niquests
        from wit_world import exports


        class Run(exports.Run):
            def run(self) -> None:
                response = niquests.get("https://httpbingo.org/get", timeout=10)
                print(response.status_code)

    Build against the Preview 2 command world, then grant network and DNS access:

    .. code:: console

        $ componentize-py -d componentize_py-0.25.0/wit -w wasi:cli/command@0.2.0 componentize app -o app.wasm
        $ wasmtime run -Sinherit-network -Sallow-ip-name-lookup=y app.wasm

.. tab:: 🔀 Async

    Use Preview 3 sockets for an asynchronous component:

    .. code:: python

        import niquests
        from wit_world import exports


        class Run(exports.Run):
            async def run(self) -> None:
                response = await niquests.aget("https://httpbingo.org/get", timeout=10)
                print(response.status_code)

    Build against the Preview 3 command world, then enable Preview 3, network, and DNS access:

    .. code:: console

        $ componentize-py -d componentize_py-0.25.0/wit -w wasi:cli/command@0.3.0 componentize app -o app.wasm
        $ wasmtime run -Sp3 -Sinherit-network -Sallow-ip-name-lookup=y app.wasm

.. warning::

    Request timeouts are currently not enforced when combining Preview 3 sockets with
    componentize-py. Async cancellation is not implemented by componentize-py, so a
    ``timeout`` value is accepted silently but does not interrupt the request or raise
    a timeout exception. This limitation does not apply to WASI HTTP 0.3: its host
    request options enforce connect, first-byte, and between-byte timeouts normally.

.. important::

    ``-Sallow-ip-name-lookup=y`` is the DNS permission for WASI sockets. Without it,
    ``inherit-network`` still exposes sockets, but URLs containing hostnames such as
    ``httpbingo.org`` cannot be resolved. It is not required by a WIT HTTP-only
    component: under ``-Shttp``, the host HTTP service performs DNS on the component's
    behalf.

.. tip::

    You can omit ``-Sallow-ip-name-lookup=y`` when using a custom Niquests resolver.
    That permission specifically exposes name resolution through the host or parent
    environment; it is not required for DNS carried over the component's permitted
    network sockets. This distinction matters for sandboxed workloads: parent DNS may
    reveal private names and addresses from an internal namespace, such as Kubernetes
    cluster DNS, even when the application only needs public Internet destinations.

    In that situation, deny host name lookup and configure an explicit external
    resolver, such as DNS over HTTPS or TLS. Ensure that the resolver can be
    bootstrapped without host DNS, for example by addressing a trusted resolver by IP
    or supplying an otherwise pre-resolved endpoint. You may also use the in-memory
    resolver if that's simpler.

The example grants network access and permission to resolve names, but no host
directory is preopened. Do not add ``--dir`` unless the application genuinely needs
host files. Be aware that Wasmtime's ``inherit-network`` grant is intentionally broad:
it exposes the host network namespace rather than only the URL shown above. In
production, prefer a host-level destination allowlist over unrestricted inherited
network access when your runtime supports one.

Niquests selects the available WASI transport automatically; application code does
not mount an adapter. Socket WIT provides native connection pooling, protocol
negotiation, WebSocket, SSE, redirects, and the usual Session behavior. A host-managed
WASI HTTP interface is also supported as a constrained fallback. See
:ref:`wasi-advanced` before choosing that contract or designing a least-authority
deployment.

.. note::

    Preview 3 and its componentize-py integration are still evolving. Pin your
    component toolchain and runtime together for reproducible deployments.

Running in the browser (Pyodide)
--------------------------------

.. versionadded:: 3.18.0

Niquests runs natively in `Pyodide <https://pyodide.org>`_ without configuration
changes. HTTP requests, WebSocket, and SSE use :class:`~niquests.Session`,
:class:`~niquests.AsyncSession`, and
:attr:`resp.extension <niquests.Response.extension>`. The adapter is selected
automatically when Pyodide is detected.

.. warning:: Synchronous interfaces require a JSPI-capable browser or Node.js
   runtime. Modern builds of Firefox, Chrome, and Node.js support JSPI.

.. tab:: 🔂 Sync

    .. code:: python

        # This exact code works in both CPython and Pyodide:
        import niquests

        resp = niquests.get("https://httpbingo.org/get")
        print(resp.json())

.. tab:: 🔀 Async

    .. code:: python

        # This exact code works in both CPython and Pyodide:
        import niquests

        resp = await niquests.aget("https://httpbingo.org/get")
        print(resp.json())

.. note:: Although Niquests exposes synchronous HTTP interfaces, prefer
   ``async``/``await`` in browsers, whose networking APIs are asynchronous.

WebSocket and SSE use the same API as described in the sections above:

.. tab:: 🔂 Sync

    .. code:: python

        from niquests import Session

        with Session() as s:
            # Behind the scenes, uses the browser's native WebSocket API
            resp = s.get("wss://echo.websocket.org")
            resp.extension.send_payload("Hello")
            print(resp.extension.next_payload())
            resp.extension.close()

            # Behind the scenes, uses fetch streaming under the hood
            resp = s.get("sse://some-server.example/events")
            while not resp.extension.closed:
                event = resp.extension.next_payload()
                if event is None:
                    break
                print(event)

.. tab:: 🔀 Async

    .. code:: python

        from niquests import AsyncSession

        async with AsyncSession() as s:
            # Behind the scenes, uses the browser's native WebSocket API
            resp = await s.get("wss://echo.websocket.org")
            await resp.extension.send_payload("Hello")
            print(await resp.extension.next_payload())
            await resp.extension.close()

            # Behind the scenes, uses fetch streaming under the hood
            resp = await s.get("sse://some-server.example/events")
            while not resp.extension.closed:
                event = await resp.extension.next_payload()
                if event is None:
                    break
                print(event)

What the browser controls
~~~~~~~~~~~~~~~~~~~~~~~~~

Under Pyodide, the browser's network stack handles the actual connections.
Some behavior differs from ordinary CPython. These are properties of the
browser sandbox rather than Niquests limitations:

- **DNS resolution** is handled by the browser. Custom resolvers, DNS over HTTPS, and protocol toggles have no effect.
- **TLS** is handled by the browser. The ``verify``, ``cert``, and
  ``tls_configuration`` parameters are ignored, and the browser uses its own certificate
  store. Consequently, :attr:`response.conn_info <niquests.Response.conn_info>` is unset.
- **CORS applies**. The remote server must include the appropriate ``Access-Control-Allow-Origin`` headers, or the browser will block the request.
- :attr:`response.http_version <niquests.Response.http_version>` is ``None``. The browser
  does not expose the negotiated HTTP protocol.
- **Certain headers cannot be set**. The browser forbids overriding ``Host``, ``Origin``, ``Cookie``, ``Connection``, and other `forbidden headers <https://developer.mozilla.org/en-US/docs/Glossary/Forbidden_header_name>`_.
- **No HTTP+Unix sockets**. Unix domain sockets are not available in the browser environment.
- **Pool sizing, HTTP version toggles, and multiplexing settings** are silently ignored because the browser manages its own connection pool.
- **Redirect history is unavailable** through the browser sandbox.
- **Disabling automatic redirects is unsupported** because intermediate responses are opaque to browser code.
- **Application-level proxy configuration is unavailable** because the browser or operating system controls proxies outside WASM/JavaScript.
- **``pre_send`` and ``early_response`` hooks** are silently ignored.
- **Extras** such as ``socks``, ``ocsp``, ``speedups``, and ``zstd`` are unavailable or unused in WASM.

These restrictions apply to all code running inside the browser sandbox.

Scheme mapping
~~~~~~~~~~~~~~

The scheme prefixes work exactly as elsewhere:

- ``sse://`` maps to ``https://`` for SSE
- ``psse://`` maps to ``http://`` for plaintext SSE
- ``wss://`` and ``ws://`` use the browser's native WebSocket

-----------------------

Ready for more? Check out the :ref:`advanced <advanced>` section.

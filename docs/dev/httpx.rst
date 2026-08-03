.. meta::
   :description: Migrate from HTTPX to Niquests, a Python HTTPX alternative with sync and async APIs, HTTP/2, HTTP/3, WebSocket, SSE, and Requests compatibility.
   :keywords: HTTPX alternative, alternative to HTTPX, migrate HTTPX, HTTPX vs Niquests, Python async HTTP client, Python HTTP/2 client, Python HTTP/3 client, Requests compatible HTTP client, Niquests

.. _httpx-to-niquests-compatibility-guide:

HTTPX → Niquests guide
======================

This guide shows how to take code written for HTTPX and migrate it to ``niquests`` API.
Wherever HTTPX differs, you’ll find the Niquests equivalent here.

.. note:: That document heavily inspire itself from the HTTPX guide "Requests to HTTPX". We took it backward as Niquests is a drop-in replacement for Requests.

Redirects
---------

HTTPX does **not** follow redirects by default and requires you to opt in::

    # HTTPX: must explicitly follow
    response = client.get(url, follow_redirects=True)

In Niquests, redirects **are** followed by default.  To disable them (i.e., mimic HTTPX default), pass::

    # Niquests: disable auto-redirects
    response = niquests.get(url, allow_redirects=False)

Or disable on a session::

    session = niquests.Session()
    session.max_redirects = 0  # will raise if any redirect is received

Client/Session instances
------------------------

In HTTPX, you use::

    client = httpx.Client(**kwargs)

To migrate, swap to Niquests' :class:`~niquests.Session`::

    session = niquests.Session(**kwargs)

Any keyword arguments that HTTPX supported on ``Client`` may not exist on
:class:`~niquests.Session`; check the Niquests docs for the
:class:`Session constructor <niquests.Session>`.

Response URLs
-------------

HTTPX’s ``response.url`` is a ``URL`` object.  
In Niquests, :attr:`response.url <niquests.Response.url>` is already a string, so you can use it directly::

    # HTTPX → str(response.url)
    # Niquests → response.url  (no conversion needed)
    print(response.url)  # e.g. 'https://www.example.com/path?query=1'

Determining the next redirect request
-------------------------------------

HTTPX exposes ``response.next_request``. In Niquests the attribute is named
:attr:`response.next <niquests.Response.next>`::

    # HTTPX
    client = httpx.Client()
    req = client.build_request("GET", url)
    while req is not None:
        resp = client.send(req)
        req = resp.next_request

    # Niquests
    session = niquests.Session()
    prepared = niquests.Request("GET", url).prepare()
    while prepared is not None:
        resp = session.send(prepared, allow_redirects=False)
        prepared = resp.next

Raw request content vs form data
--------------------------------

HTTPX distinguishes ``content=`` for raw bytes/text from ``data=`` for form submissions::

    # HTTPX
    httpx.post(url, content=b"raw bytes")
    httpx.post(url, data={"field": "value"})

In Niquests, use::

    niquests.post(url, data=b"raw bytes")      # raw bytes/text are passed via `data=`
    niquests.post(url, data={"field": "value"})  # form-encoded by default

Note: Niquests has no separate ``content`` parameter.

File uploads
------------

HTTPX enforces binary-mode file handles. Niquests is more lenient but still requires binary for non-text uploads::

    # HTTPX
    with open('file.bin', 'rb') as f:
        httpx.post(url, files={'file': f})

    # Niquests
    with open('file.bin', 'rb') as f:
        niquests.post(url, files={'file': f})

Content encoding
----------------

Both HTTPX and Niquests encodes str bodies as UTF-8 by default::

    # HTTPX: content="ñ" → UTF-8
    httpx.post(url, content="ñ")

    # Niquests: content="ñ" → UTF-8
    niquests.post(url, data="ñ")

Cookies
-------

HTTPX only allows cookies on the client::

    # HTTPX
    client = httpx.Client(cookies={'a': '1'})

Niquests also supports per-request cookies::

    # HTTPX disallowed: client.post(..., cookies=...)
    # Niquests equivalent:
    session = niquests.Session()
    session.cookies.update({'a': '1'})
    # or per request:
    niquests.get(url, cookies={'a': '1'})

Status codes constants
----------------------

HTTPX provides ``codes.NOT_FOUND`` (upper-case) and ``codes.not_found`` (lower).  
Niquests only provides lower-case::

    # HTTPX → codes.NOT_FOUND or codes.not_found
    # Niquests → codes.not_found
    if response.status_code == niquests.codes.not_found:
        ...

Streaming responses
-------------------

HTTPX uses a ``.stream()`` context::

    with httpx.stream("GET", url) as resp:
        for chunk in resp.iter_bytes():
            ...

In Niquests, pass ``stream=True`` to any existing methods and iterate::

    with niquests.get(url, stream=True) as resp:
        for chunk in resp.iter_content(chunk_size=-1):
            ...

- :meth:`resp.iter_content() <niquests.Response.iter_content>` ↔︎ ``resp.iter_bytes()``
- ``resp.iter_lines()`` exists in both

Timeouts
--------

Both HTTPX and Niquests have sensible defaults.

In Niquests, read operation (GET, HEAD, OPTIONS) default to 30s timeout otherwise (POST, DELETE, PUT, ...) 120s.
Those are very conservative default that you should override any time it suit your needs.

Previously you wrote this to set a global timeout::

    with httpx.Client(timeout=httpx.Timeout(connect=10, total=60)):
        ...

You may now achieve the same using::

    with niquests.Session(timeout=niquests.TimeoutConfiguration(connect=10, total=60)) as s:
        ...

.. note:: Instead of a :class:`~niquests.TimeoutConfiguration` you may pass a simple integer or float instead.

Proxies / mounts
----------------

HTTPX uses ``mounts={...}`` with full URL schemes::

    httpx.Client(mounts={'http://': transport, 'https://': transport})

In Niquests, you use a ``proxies`` dict::

    session = niquests.Session()
    session.proxies.update({'http': 'http://proxy.example', 'https': 'https://proxy.example'})
    # or per request:
    niquests.get(url, proxies={'http': '...', 'https': '...'})

SSL configuration
-----------------

HTTPX requires SSL settings on the client::

    client = httpx.Client(verify='/path/to/ca.pem')

Niquests allows SSL args per-request or on a Session::

    # per request
    niquests.get(url, verify='/path/to/ca.pem')

    # or on Session
    session = niquests.Session()
    session.verify = '/path/to/ca.pem'

Request bodies on “body-less” methods
-------------------------------------

HTTPX disallows ``content`` on methods like ``.get()``, recommending ``.request()``::

    # HTTPX: must use .request()
    httpx.request("DELETE", url, content=b"data")

Niquests lets you pass a body directly::

    # Niquests: delete with body
    niquests.delete(url, data=b"data")
    # or use .request()
    niquests.request("DELETE", url, data=b"data")

.. warning:: Passing bodies through DELETE, GET or HEAD is not recommended.

Success checks
--------------

HTTPX uses ``response.is_success``; Niquests has
:attr:`response.ok <niquests.Response.ok>`::

    # HTTPX
    if response.is_success:
        ...

    # Niquests
    if response.ok:
        ...

Note: Niquests' :attr:`ok <niquests.Response.ok>` is equivalent to checking
``200 <= status_code < 400``.

Prepared requests
-----------------

HTTPX's ``Client.build_request`` replaces Niquests'
:meth:`Request.prepare() <niquests.Request.prepare>`::

    # HTTPX
    req = client.build_request("GET", url)

    # Niquests
    req = niquests.Request("GET", url)
    prepared = session.prepare_request(req)

HTTP/2
------

HTTPX disable HTTP/2 by default and requires you to install an extra dependency to make it work.
Whereas Niquests enable HTTP/2 AND HTTP/3 by default.

.. note:: HTTPX don't support HTTP/3 by any official ways.

To mimic HTTPX default behavior::

    client = httpx.Client(http2=False)  # default value

Do::

    session = niquests.Session(disable_http2=True, disable_http3=True)

With this, Niquests will ever only establish good old HTTP/1.1 requests.

Async
-----

As HTTPX, Niquests does mirror its sync interfaces to async.

For example::

    session = niquests.Session()

Becomes::

    session = niquests.AsyncSession()

And::

    resp = niquests.get(...)

Transforms to::

    resp = await niquests.aget(...)

Mocking & testing
-----------------

- HTTPX: RESPX (https://github.com/lundberg/respx)  
- Niquests: responses (https://github.com/getsentry/responses) or requests-mock (https://requests-mock.readthedocs.io)

.. note:: See the migration guide for responses or requests-mock in extensions.

Caching
-------

- HTTPX: Hishel (https://hishel.com)  
- Niquests: cachecontrol (https://github.com/psf/cachecontrol) or requests-cache (https://github.com/requests-cache/requests-cache)

.. note:: See the migration guide for cachecontrol or requests-cache in extensions.

Networking layer
----------------

- HTTPX: uses HTTPCore under the hood  
- Niquests: built atop urllib3-future (fork of known urllib3)

Query parameters & form data
----------------------------

HTTPX requires explicit lists in dicts; it does **not** accept lists of tuples or omit ``None`` values.  Niquests supports both::

    # HTTPX: httpx.get(..., params={'a': ['1','2'], 'b': None})
    # Niquests equivalent:
    niquests.get(url, params=[('a','1'), ('a','2'), ('b', '')])
    # or omit None:
    niquests.get(url, params={'a':['1','2']})

Event hooks
-----------

- HTTPX event hooks can **observe** but not **mutate**  
- Niquests hooks can mutate both :class:`Request <niquests.Request>` and
  :class:`Response <niquests.Response>`.

.. code-block:: python

    # Niquests example: log each request
    def print_url(r, *args, **kwargs):
        print("URL:", r.url)

    session = niquests.Session()
    session.hooks['response'] = [print_url]

Whenever you see an HTTPX-specific parameter or method, look for its closest Niquests counterpart as shown above.
Happy migrating!


ASGI/WSGI testing
-----------------

.. versionadded:: 3.17.0

You can do ASGI or WSGI testing using Niquests.

In HTTPX you wrote something like:

.. code-block:: python

    from flask import Flask
    import httpx


    app = Flask(__name__)

    @app.route("/")
    def hello():
        return "Hello World!"

    transport = httpx.WSGITransport(app=app)
    with httpx.Client(transport=transport, base_url="http://testserver") as client:
        r = client.get("/")
        assert r.status_code == 200
        assert r.text == "Hello World!"

Now you can easily achieve the same with Niquests:

.. code-block:: python

    from flask import Flask
    import niquests


    app = Flask(__name__)

    @app.route("/")
    def hello():
        return "Hello World!"

    with niquests.Session(app=app) as s:
        r = s.get("/")

        assert r.status_code == 200
        assert r.text == "Hello World!"

.. note:: The same goes for ASGI testing, but instead of using
   :class:`Session <niquests.Session>`, you'll use
   :class:`AsyncSession <niquests.AsyncSession>` instead.

.. warning:: ASGI lifespan startup/shutdown is not handled by Niquests (neither does httpx). You'll use something like asgi-lifespan (https://github.com/florimondmanca/asgi-lifespan#usage) to handle that part.

With FastAPI you could have been used to:

.. code-block:: python

    from fastapi import TestClient

    client = TestClient(app)

    response = client.get("/")

You can do so with Niquests also!

.. code-block:: python

    from niquests import Session

    client = Session(app=app)

    response = client.get("/")

.. note:: TestClient exposed in FastAPI is actually starlette.TestClient. Starlette is using httpx deep under the hood as an optional dependency.

.. warning:: Like starlette.TestClient we are defeating the purpose of true async with threading. It's there for convenience only, we recommend you to leverage async/await as a best practice.

.. warning:: The synchronous Session handle lifespan startup/shutdown events opposed to the pure asynchronous implementation. Also, for convenience.

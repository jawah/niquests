.. _httpx-to-niquests-compatibility-guide:

HTTPX → Niquests Guide
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

Client/Session Instances
------------------------

In HTTPX, you use::

    client = httpx.Client(**kwargs)

To migrate, swap to Niquests’ ``Session``::

    session = niquests.Session(**kwargs)

Any keyword arguments that HTTPX supported on ``Client`` may not exist on ``Session``; check the Niquests docs for ``Session.__init__``.

Response URLs
-------------

HTTPX’s ``response.url`` is a ``URL`` object.  
In Niquests, ``response.url`` is already a string, so you can use it directly::

    # HTTPX → str(response.url)
    # Niquests → response.url  (no conversion needed)
    print(response.url)  # e.g. 'https://www.example.com/path?query=1'

Determining the Next Redirect Request
-------------------------------------

HTTPX exposes ``response.next_request``.  In Niquests the attribute is named ``response.next``::

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

Raw Request Content vs Form Data
--------------------------------

HTTPX distinguishes ``content=`` for raw bytes/text from ``data=`` for form submissions::

    # HTTPX
    httpx.post(url, content=b"raw bytes")
    httpx.post(url, data={"field": "value"})

In Niquests, use::

    niquests.post(url, data=b"raw bytes")      # raw bytes/text are passed via `data=`
    niquests.post(url, data={"field": "value"})  # form-encoded by default

Note: Niquests has no separate ``content`` parameter.

File Uploads
------------

HTTPX enforces binary-mode file handles. Niquests is more lenient but still requires binary for non-text uploads::

    # HTTPX
    with open('file.bin', 'rb') as f:
        httpx.post(url, files={'file': f})

    # Niquests
    with open('file.bin', 'rb') as f:
        niquests.post(url, files={'file': f})

Content Encoding
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

Status Codes Constants
----------------------

HTTPX provides ``codes.NOT_FOUND`` (upper-case) and ``codes.not_found`` (lower).  
Niquests only provides lower-case::

    # HTTPX → codes.NOT_FOUND or codes.not_found
    # Niquests → codes.not_found
    if response.status_code == niquests.codes.not_found:
        ...

Streaming Responses
-------------------

HTTPX uses a ``.stream()`` context::

    with httpx.stream("GET", url) as resp:
        for chunk in resp.iter_bytes():
            ...

In Niquests, pass ``stream=True`` to any existing methods and iterate::

    with niquests.get(url, stream=True) as resp:
        for chunk in resp.iter_content(chunk_size=-1):
            ...

- ``resp.iter_content()`` ↔︎ ``resp.iter_bytes()``
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

.. note:: Instead of a ``TimeoutConfiguration`` you may pass a simple integer or float instead.

Proxies / Mounts
----------------

HTTPX uses ``mounts={...}`` with full URL schemes::

    httpx.Client(mounts={'http://': transport, 'https://': transport})

In Niquests, you use a ``proxies`` dict::

    session = niquests.Session()
    session.proxies.update({'http': 'http://proxy.example', 'https': 'https://proxy.example'})
    # or per request:
    niquests.get(url, proxies={'http': '...', 'https': '...'})

SSL Configuration
-----------------

HTTPX requires SSL settings on the client::

    client = httpx.Client(verify='/path/to/ca.pem')

Niquests allows SSL args per-request or on a Session::

    # per request
    niquests.get(url, verify='/path/to/ca.pem')

    # or on Session
    session = niquests.Session()
    session.verify = '/path/to/ca.pem'

Request Bodies on “Body-less” Methods
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

Success Checks
--------------

HTTPX uses ``response.is_success``; Niquests has ``response.ok``::

    # HTTPX
    if response.is_success:
        ...

    # Niquests
    if response.ok:
        ...

Note: Niquests’ ``ok`` is equivalent to checking ``200 <= status_code < 400``.

Prepared Requests
-----------------

HTTPX’s ``Client.build_request`` replaces Niquests’ ``Request.prepare()``::

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

Mocking & Testing
-----------------

- HTTPX: RESPX (https://github.com/lundberg/respx)  
- Niquests: responses (https://github.com/getsentry/responses) or requests-mock (https://requests-mock.readthedocs.io)

.. note:: See the migration guide for responses or requests-mock in extensions.

Caching
-------

- HTTPX: Hishel (https://hishel.com)  
- Niquests: cachecontrol (https://github.com/cachecontrol/cachecontrol) or requests-cache (https://github.com/requests-cache/requests-cache)

.. note:: See the migration guide for cachecontrol or requests-cache in extensions.

Networking Layer
----------------

- HTTPX: uses HTTPCore under the hood  
- Niquests: built atop urllib3-future (fork of known urllib3)

Query Parameters & Form Data
----------------------------

HTTPX requires explicit lists in dicts; it does **not** accept lists of tuples or omit ``None`` values.  Niquests supports both::

    # HTTPX: httpx.get(..., params={'a': ['1','2'], 'b': None})
    # Niquests equivalent:
    niquests.get(url, params=[('a','1'), ('a','2'), ('b', '')])
    # or omit None:
    niquests.get(url, params={'a':['1','2']})

Event Hooks
-----------

- HTTPX event hooks can **observe** but not **mutate**  
- Niquests hooks can mutate both ``Request`` and ``Response``.

.. code-block:: python

    # Niquests example: log each request
    def print_url(r, *args, **kwargs):
        print("URL:", r.url)

    session = niquests.Session()
    session.hooks['response'] = [print_url]

Whenever you see an HTTPX-specific parameter or method, look for its closest Niquests counterpart as shown above.
Happy migrating!

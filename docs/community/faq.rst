.. _faq:

Frequently Asked Questions
==========================

This part of the documentation answers common questions about Niquests.

Encoded Data?
-------------

Niquests automatically decompresses gzip-encoded responses, and does
its best to decode response content to unicode when possible.

When either the `brotli <https://pypi.org/project/Brotli/>`_ or `brotlicffi <https://pypi.org/project/brotlicffi/>`_
package is installed, requests also decodes Brotli-encoded responses.

You can get direct access to the raw response (and even the socket),
if needed as well.


Custom User-Agents?
-------------------

Niquests allows you to easily override User-Agent strings, along with
any other HTTP Header. See `documentation about headers <https://niquests.readthedocs.io/en/latest/user/quickstart/#custom-headers>`_.


What are "hostname doesn't match" errors?
-----------------------------------------

These errors occur when :ref:`SSL certificate verification <verification>`
fails to match the certificate the server responds with to the hostname
Niquests thinks it's contacting. If you're certain the server's SSL setup is
correct (for example, because you can visit the site with your browser).

`Server-Name-Indication`_, or SNI, is an official extension to SSL where the
client tells the server what hostname it is contacting. This is important
when servers are using `Virtual Hosting`_. When such servers are hosting
more than one SSL site they need to be able to return the appropriate
certificate based on the hostname the client is connecting to.

Python 3 already includes native support for SNI in their SSL modules.

.. _`Server-Name-Indication`: https://en.wikipedia.org/wiki/Server_Name_Indication
.. _`virtual hosting`: https://en.wikipedia.org/wiki/Virtual_hosting


What are "OverwhelmedTraffic" errors?
-------------------------------------

You may witness: " Cannot select a disposable connection to ease the charge ".

Basically, it means that your pool of connections is saturated and we were unable to open a new connection.
If you wanted to run 32 threads sharing the same ``Session`` objects, you want to allow
up to 32 connections per host.

Do as follow::

    import niquests

    with niquests.Session(pool_maxsize=32) as s:
        ...


What is "urllib3.future"?
-------------------------

It is a fork of the well know **urllib3** library, you can easily imagine that
Niquests would have been completely unable to serve that much feature with the
existing **urllib3** library.

**urllib3.future** is independent, managed separately and completely compatible with
its counterpart (API-wise).

Shadow-Naming
~~~~~~~~~~~~~

Your environment may or may not include the legacy urllib3 package in addition to urllib3.future.
So doing::

    import urllib3

May actually import either urllib3 or urllib3.future.
But fear not, if your script was compatible with urllib3, it will most certainly work
out-of-the-box with urllib3.future.

This behavior was chosen to ensure the highest level of compatibility for your migration,
ensuring the minimum friction during the migration between Requests to Niquests.

Cohabitation
~~~~~~~~~~~~

You may have both urllib3 and urllib3.future installed if wished.
Niquests will use the secondary entrypoint for urllib3.future internally.

It does not change anything for you. You may still pass ``urllib3.Retry`` and
``urllib3.Timeout`` regardless of the cohabitation, Niquests will do
the translation internally.

What are my headers are lowercased?
-----------------------------------

This may come as a surprise for some of you. Until Requests-era, header keys could arrive
as they were originally sent (case-sensitive). This is possible thanks to HTTP/1.1 protocol.
Nonetheless, RFCs specifies that header keys are *case-insensible*, that's why both Requests
and Niquests ships with ``CaseInsensitiveDict`` class.

So why did we alter it then?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The answer is quite simple, we support HTTP/2, and HTTP/3 over QUIC! The newer protocols enforce
header case-insensitivity and we can only forward them as-is (lowercased).

Can we revert this behavior? Any fallback?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes... kind of!
Niquests ships with a nice alternative to ``CaseInsensitiveDict`` that is ``kiss_headers.Headers``.
You may access it through the ``oheaders`` property of your usual Response, Request and PreparedRequest.

Am I obligated to install qh3?
------------------------------

No. But by default, it could be picked for installation. You may remove it safely at the cost
of loosing HTTP/3 over QUIC and OCSP certificate revocation status.

A shortcut would be::

    $ pip uninstall qh3

.. warning:: Your site-packages is shared, thus it is possible that other libraries depends on some of the listed programs. Do it with care!

What are "pem lib" errors?
--------------------------

Ever encountered something along::

    $ SSLError: [SSL] PEM lib (_ssl.c:2532)

Yes? Usually it means that you tried to load a certificate (CA or client cert) that is malformed.

What does malformed means?
~~~~~~~~~~~~~~~~~~~~~~~~~

Could be just a missing newline character *RC*, or wrong format like passing a DER file instead of a PEM
encoded certificate.

If none of those seems related to your situation, feel free to open an issue at https://github.com/jawah/niquests/issues

Why HTTP/2 and HTTP/3 seems slower than HTTP/1.1?
-------------------------------------------------

Because you are not leveraging its potential properly. Most of the time, developers tends to
make a request and immediately consume the response afterward. Let's call that making OneToOne requests.
HTTP/2, and HTTP/3 both requires more computational power for a single request than HTTP/1.1 (in OneToOne context).
The true reason for them to exist, is not the OneToOne scenario.

So, how to remedy that?

You have multiple choices:

1. Using multiplexing in a synchronous context or asynchronous
2. Starting threads
3. Using async with concurrent tasks

This example will quickly demonstrate, how to utilize and leverage your HTTP/2 connection with ease::

    from time import time
    from niquests import Session

    #: You can adjust it as you want and verify the multiplexed advantage!
    REQUEST_COUNT = 10
    REQUEST_URL = "https://httpbin.org/delay/1"

    def make_requests(url: str, count: int, use_multiplexed: bool):
      before = time()

      responses = []

      with Session(multiplexed=use_multiplexed) as s:
        for _ in range(count):
          responses.append(s.get(url))
          print(f"request {_+1}...OK")
        print([r.status_code for r in responses])

      print(
          f"{time() - before} seconds elapsed ({'multiplexed' if use_multiplexed else 'standard'})"
      )

    #: Let's start with the same good old request one request at a time.
    print("> Without multiplexing:")
    make_requests(REQUEST_URL, REQUEST_COUNT, False)
    #: Now we'll take advantage of a multiplexed connection.
    print("> With multiplexing:")
    make_requests(REQUEST_URL, REQUEST_COUNT, True)

.. note:: This piece of code showcase how to emit concurrent requests in a synchronous context without threads and async.

We would gladly discuss potential implementations if needed, just open a new issue at https://github.com/jawah/niquests/issues

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

This behavior was chosen to ensure the highest level of compatibility with your migration,
ensuring the minimum friction during the migration between Requests and Niquests.

Cohabitation
~~~~~~~~~~~~

You may have both urllib3 and urllib3.future installed if wished.
Niquests will use the secondary entrypoint for urllib3.future internally.

It does not change anything for you. You may still pass ``urllib3.Retry`` and
``urllib3.Timeout`` regardless of the cohabitation, Niquests will do
the translation internally.

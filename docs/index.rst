.. Requests documentation master file, created by
   sphinx-quickstart on Sun Feb 13 23:54:25 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Niquests: HTTP for Humans™
==========================

Release v\ |version|. (:ref:`Installation <install>`)


.. image:: https://static.pepy.tech/badge/niquests/month
    :target: https://pepy.tech/project/niquests
    :alt: Niquests Downloads Per Month Badge
    
.. image:: https://img.shields.io/pypi/l/niquests.svg
    :target: https://pypi.org/project/niquests/
    :alt: License Badge

.. image:: https://img.shields.io/pypi/pyversions/niquests.svg
    :target: https://pypi.org/project/niquests/
    :alt: Python Version Support Badge

**Niquests** is an elegant and simple HTTP library for Python, built for human beings. It
is designed to be a drop-in replacement for **Requests** that is no longer under feature freeze.

-------------------

**Behold, the power of Niquests**::

   >>> import niquests
   >>> s = niquests.Session(resolver="doh+google://", multiplexed=True)
   >>> r = s.get('https://pie.dev/basic-auth/user/pass', auth=('user', 'pass'))
   >>> r.status_code
   200
   >>> r.headers['content-type']
   'application/json; charset=utf8'
   >>> r.oheaders.content_type.charset
   'utf8'
   >>> r.encoding
   'utf-8'
   >>> r.text
   '{"authenticated": true, ...'
   >>> r.json()
   {'authenticated': True, ...}
   >>> r
   <Response HTTP/3 [200]>
   >>> r.ocsp_verified
   True
   >>> r.conn_info.established_latency
   datetime.timedelta(microseconds=38)

See `similar code, sans Niquests <https://gist.github.com/973705>`_.


**Niquests** allows you to send HTTP/1.1, HTTP/2 and HTTP/3 requests extremely easily.
There's no need to manually add query strings to your
URLs, or to form-encode your POST data. Keep-alive and HTTP connection pooling
are 100% automatic, thanks to `urllib3.future <https://github.com/jawah/urllib3.future>`_.

Beloved Features
----------------

Niquests is ready for today's web.

- DNS over HTTPS, DNS over QUIC, DNS over TLS, and DNS over UDP
- Automatic Content Decompression and Decoding
- OS truststore by default, no more certifi!
- OCSP Certificate Revocation Verification
- Advanced connection timings inspection
- In-memory certificates (CAs, and mTLS)
- Browser-style TLS/SSL Verification
- Sessions with Cookie Persistence
- Keep-Alive & Connection Pooling
- International Domains and URLs
- Automatic honoring of `.netrc`
- Basic & Digest Authentication
- Familiar `dict`–like Cookies
- Object-oriented headers
- Multi-part File Uploads
- Chunked HTTP Requests
- Fully type-annotated!
- SOCKS Proxy Support
- Connection Timeouts
- Streaming Downloads
- HTTP/2 by default
- HTTP/3 over QUIC
- Happy Eyeballs
- Multiplexed!
- Thread-safe!
- DNSSEC!
- Async!

Niquests officially supports Python 3.7+, and runs great on PyPy.


The User Guide
--------------

This part of the documentation, which is mostly prose, begins with some
background information about Niquests, then focuses on step-by-step
instructions for getting the most out of Niquests.

.. toctree::
   :maxdepth: 2

   user/install
   user/quickstart
   user/advanced
   user/authentication


The Community Guide
-------------------

This part of the documentation, which is mostly prose, details the
Niquests ecosystem and community.

.. toctree::
   :maxdepth: 2

   dev/migrate
   community/recommended
   community/faq
   community/support
   community/vulnerabilities
   community/release-process

.. toctree::
   :maxdepth: 1

   community/updates

The API Documentation / Guide
-----------------------------

If you are looking for information on a specific function, class, or method,
this part of the documentation is for you.

.. toctree::
   :maxdepth: 2

   api


The Contributor Guide
---------------------

If you want to contribute to the project, this part of the documentation is for
you.

.. toctree::
   :maxdepth: 3

   dev/contributing
   dev/authors

There are no more guides. You are now guideless.
Good luck.

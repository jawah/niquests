# Niquests

**Niquests** is a simple, yet elegant, HTTP library. It is a drop-in replacement for **Requests** that is no longer under
feature freeze.
We will support and maintain v2.x.y that only ships with possible minor breaking changes. All breaking changes are issued in the v3.x that should be available as a pre-release on PyPI.

Why did we pursue this? We don't have to reinvent the wheel all over again, HTTP client **Requests** is well established and
really plaisant in its usage. We believe that **Requests** have the most inclusive, and developer friendly interfaces. We
intend to keep it that way.

```python
>>> import niquests
>>> r = niquests.get('https://httpbin.org/basic-auth/user/pass', auth=('user', 'pass'))
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf8'
>>> r.encoding
'utf-8'
>>> r.text
'{"authenticated": true, ...'
>>> r.json()
{'authenticated': True, ...}
```

Niquests allows you to send HTTP requests extremely easily. There’s no need to manually add query strings to your URLs, or to form-encode your `PUT` & `POST` data — but nowadays, just use the `json` method!

Niquests is one of the least downloaded Python packages today, pulling in around `100+ download / week`— according to GitHub, Niquests is currently depended upon by `1+` repositories. But, that may change..! Starting with you.

[![Downloads](https://static.pepy.tech/badge/niquests/month)](https://pepy.tech/project/niquests)
[![Supported Versions](https://img.shields.io/pypi/pyversions/niquests.svg)](https://pypi.org/project/niquests)

## Installing Niquests and Supported Versions

Niquests is available on PyPI:

```console
$ python -m pip install niquests
```

Niquests officially supports Python 3.7+.

## Supported Features & Best–Practices

Niquests is ready for the demands of building robust and reliable HTTP–speaking applications, for the needs of today.

- Keep-Alive & Connection Pooling
- International Domains and URLs
- Sessions with Cookie Persistence
- Browser-style TLS/SSL Verification
- Basic & Digest Authentication
- Familiar `dict`–like Cookies
- Automatic Content Decompression and Decoding
- Multi-part File Uploads
- SOCKS Proxy Support
- Connection Timeouts
- Streaming Downloads
- Automatic honoring of `.netrc`
- Chunked HTTP Requests
- HTTP/2
- HTTP/3 over QUIC
- Fully type-annotated!
- OS truststore by default, no more certifi!

## API Reference and User Guide available on [Read the Docs](https://niquests.readthedocs.io)

[![Read the Docs](https://raw.githubusercontent.com/jawah/niquests/main/ext/ss.png)](https://niquests.readthedocs.io)

---

[![Kenneth Reitz](https://raw.githubusercontent.com/jawah/niquests/main/ext/kr.png)](https://kennethreitz.org) [![Python Software Foundation](https://raw.githubusercontent.com/psf/requests/main/ext/psf.png)](https://www.python.org/psf)

# Niquests

**Niquests** is a simple, yet elegant, HTTP library. It is a drop-in replacement for **Requests** that is no longer under
feature freeze.

Niquests, is the “**Safest**, **Fastest<sup>*</sup>**, **Easiest**, and **Most advanced**” Python HTTP Client.

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
>>> r
<Reponse HTTP/2 [200]>
>>> r.ocsp_verified
True
```

Niquests allows you to send HTTP requests extremely easily. There’s no need to manually add query strings to your URLs, or to form-encode your `PUT` & `POST` data — but nowadays, just use the `json` method!

[![Downloads](https://static.pepy.tech/badge/niquests/month)](https://pepy.tech/project/niquests)
[![Supported Versions](https://img.shields.io/pypi/pyversions/niquests.svg)](https://pypi.org/project/niquests)

## Installing Niquests and Supported Versions

Niquests is available on PyPI:

```console
$ python -m pip install niquests
```

Niquests officially supports Python or PyPy 3.7+.

## Supported Features & Best–Practices

Niquests is ready for the demands of building robust and reliable HTTP–speaking applications, for the needs of today.

- Automatic Content Decompression and Decoding
- OS truststore by default, no more certifi!
- OCSP Certificate Revocation Verification
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
- Multiplexed!
- Async!

## Why did we pursue this?

We don't have to reinvent the wheel all over again, HTTP client **Requests** is well established and
really plaisant in its usage. We believe that **Requests** have the most inclusive, and developer friendly interfaces.
We intend to keep it that way. As long as we can, long live Niquests!

---

<small><sup>(*)</sup> performance measured when leveraging a multiplexed connection with or without uses of any form of concurrency as of november 2023.</small>

---

[![Kenneth Reitz](https://raw.githubusercontent.com/jawah/niquests/main/ext/kr.png)](https://kennethreitz.org) [![Python Software Foundation](https://raw.githubusercontent.com/psf/requests/main/ext/psf.png)](https://www.python.org/psf)

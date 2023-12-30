<div align="center">
    <img src="https://user-images.githubusercontent.com/9326700/282852138-160f32e9-e6cf-495f-b39d-99891602acf9.png" alt="Niquests Logo"/>
</div>

**Niquests** is a simple, yet elegant, HTTP library. It is a drop-in replacement for **Requests** that is no longer under
feature freeze.

Niquests, is the “**Safest**, **Fastest<sup>*</sup>**, **Easiest**, and **Most advanced**” Python HTTP Client. Production Ready!

✔️ **Try before you switch:** [See Multiplexed in Action](https://replit.com/@ahmedtahri4/Python#main.py)<br>
📖 **See why you should switch:** [Read about 10 reasons why](https://medium.com/dev-genius/10-reasons-you-should-quit-your-http-client-98fd4c94bef3)

```python
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
- Network settings fine-tuning
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
- Thread-safe!
- DNSSEC!
- Async!

Need something more? Create an issue, we listen.

## Why did we pursue this?

For many years now, **Requests** has been frozen and blocked millions of developers, left in a vegetative state
regarding evolutions in the field.

We don't have to reinvent the wheel all over again, HTTP client **Requests** is well established and
really plaisant in its usage. We believe that **Requests** have the most inclusive, and developer friendly interfaces.
We intend to keep it that way. As long as we can, long live Niquests!

How about a nice refresher with a mere `CTRL+H` _import requests_ **to** _import niquests as requests_ ?

## 💼 For Enterprise

Professional support for Niquests is available as part of the [Tidelift
Subscription][1]. Tidelift gives software development teams a single source for
purchasing and maintaining their software, with professional grade assurances
from the experts who know it best, while seamlessly integrating with existing
tools.

[1]: https://tidelift.com/subscription/pkg/pypi-niquests?utm_source=pypi-niquests&utm_medium=readme

---

<small><sup>(*)</sup> performance measured when leveraging a multiplexed connection with or without uses of any form of concurrency as of november 2023. The research compared `httpx`, `requests`, `aiohttp` against `niquests`.</small>

---

[![Kenneth Reitz](https://raw.githubusercontent.com/jawah/niquests/main/ext/kr.png)](https://kennethreitz.org)

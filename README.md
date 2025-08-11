<div align="center">
    <img src="https://user-images.githubusercontent.com/9326700/282852138-160f32e9-e6cf-495f-b39d-99891602acf9.png" alt="Niquests Logo"/>
</div>

**Niquests** is a simple, yet elegant, HTTP library. It is a drop-in replacement for **Requests**, which is under feature freeze.

Niquests, is the “**Safest**, **Fastest[^10]**, **Easiest**, and **Most advanced**” Python HTTP Client. Production Ready!

✔️ **Try before you switch:** [See Multiplexed in Action](https://replit.com/@ahmedtahri4/Python#main.py)<br>
📖 **See why you should switch:** [Read about 10 reasons why](https://medium.com/@ahmed.tahri/10-reasons-you-should-quit-your-http-client-98fd4c94bef3), and ["_Revived the promise made six years ago for Requests 3_"](https://medium.com/@ahmed.tahri/revived-the-promise-made-six-years-ago-for-requests-3-37b440e6a064)<br>
✨ **You were used to betamax, requests-mock, responses, ...?** [See how they still work! We got you covered.](https://niquests.readthedocs.io/en/latest/community/extensions.html)

<details>
  <summary>👆 <b>Look at the feature table comparison</b> against <i>requests, httpx and aiohttp</i>!</summary>

| Feature                                    |    niquests    | requests  |     httpx     | aiohttp       |
|--------------------------------------------|:--------------:|:---------:|:-------------:|---------------|
| `HTTP/1.1`                                 |       ✅        |     ✅     |       ✅       | ✅             |
| `HTTP/2`                                   |       ✅        |     ❌     |     ✅[^7]     | ❌             |
| `HTTP/3 over QUIC`                         |       ✅        |     ❌     |       ❌       | ❌             |
| `Synchronous`                              |       ✅        |     ✅     |       ✅       | _N/A_[^1]     |
| `Asynchronous`                             |       ✅        |     ❌     |       ✅       | ✅             |
| `Thread Safe`                              |       ✅        |     ✅     |     ❌[^5]     | _N/A_[^1]     |
| `Task Safe`                                |       ✅        | _N/A_[^2] |       ✅       | ✅             |
| `OS Trust Store`                           |       ✅        |     ❌     |       ❌       | ❌             |
| `Multiplexing`                             |       ✅        |     ❌     | _Limited_[^3] | ❌             |
| `DNSSEC`                                   |     ✅[^11]     |     ❌     |       ❌       | ❌             |
| `Customizable DNS Resolution`              |       ✅        |     ❌     |       ❌       | ✅             |
| `DNS over HTTPS`                           |       ✅        |     ❌     |       ❌       | ❌             |
| `DNS over QUIC`                            |       ✅        |     ❌     |       ❌       | ❌             |
| `DNS over TLS`                             |       ✅        |     ❌     |       ❌       | ❌             |
| `Multiple DNS Resolver`                    |       ✅        |     ❌     |       ❌       | ❌             |
| `Network Fine Tuning & Inspect`            |       ✅        |     ❌     | _Limited_[^6] | _Limited_[^6] |
| `Certificate Revocation Protection`        |       ✅        |     ❌     |       ❌       | ❌             |
| `Session Persistence`                      |       ✅        |     ✅     |       ✅       | ✅             |
| `In-memory Certificate CA & mTLS`          |       ✅        |     ❌     | _Limited_[^4] | _Limited_[^4] |
| `SOCKS 4/5 Proxies`                        |       ✅        |     ✅     |       ✅       | ❌             |
| `HTTP/HTTPS Proxies`                       |       ✅        |     ✅     |       ✅       | ✅             |
| `TLS-in-TLS Support`                       |       ✅        |     ✅     |       ✅       | ✅             |
| `Direct HTTP/3 Negotiation`                |     ✅[^9]      |  N/A[^8]  |    N/A[^8]    | N/A[^8]       |
| `Happy Eyeballs`                           |       ✅        |     ❌     |       ❌       | ✅             |
| `Package / SLSA Signed`                    |       ✅        |     ❌     |       ❌       | ✅             |
| `HTTP/2 with prior knowledge (h2c)`        |       ✅        |     ❌     |       ✅       | ❌             |
| `Post-Quantum Security`                    | _Limited_[^12] |     ❌     |       ❌       | ❌             |
| `HTTP Trailers`                            |       ✅        |     ❌     |       ❌       | ❌             |
| `Early Responses`                          |       ✅        |     ❌     |       ❌       | ❌             |
| `WebSocket over HTTP/1`                    |       ✅        |  ❌[^14]   |    ❌[^14]     | ✅             |
| `WebSocket over HTTP/2 and HTTP/3`         |     ✅[^13]     |     ❌     |       ❌       | ❌             |
| `Automatic Ping for HTTP/2+`               |       ✅        |    N/A    |       ❌       | N/A           |
| `Automatic Connection Upgrade / Downgrade` |       ✅        |    N/A    |       ❌       | N/A           |
| `Server Side Event (SSE)`                  |       ✅        |     ❌     |       ❌       | ❌             |
</details>

<details>
  <summary>📈 <b>Look at the performance comparison</b> against <i>them</i>!</summary>

_Scenario:_ Fetch a thousand requests using 10 tasks or threads, each with a hundred requests using a single pool of connection.

**High-Level APIs**

| Client   | Average Delay to Complete | Notes                        |
|----------|---------------------------|------------------------------|
| requests | 987 ms or ~1013 req/s     | ThreadPoolExecutor. HTTP/1.1 |
| httpx    | 720 ms or ~1389 req/s     | Asyncio. HTTP/2              |
| niquests | 340 ms or ~2941 req/s     | Asyncio. HTTP/2              |

**Simplified APIs**

| Client        | Average Delay to Complete | Notes                        |
|---------------|---------------------------|------------------------------|
| requests core | 643 ms or ~1555 req/s     | ThreadPoolExecutor. HTTP/1.1 |
| httpx core    | 490 ms or ~2000 req/s     | Asyncio. HTTP/2              |
| aiohttp       | 210 ms or ~4762 req/s     | Asyncio. HTTP/1.1            |
| niquests core | 160 ms or ~6200 req/s     | Asyncio. HTTP/2              |

Did you give up on HTTP/2 due to performance concerns? Think again! Do you realize that you can get 3 times faster with the same CPU if you ever switched to Niquests from Requests?
Multiplexing and response lazyness open up a wide range of possibilities! Want to learn more about the tests? scripts? reasoning?

Take a deeper look at https://github.com/Ousret/niquests-stats
</details>

```python
>>> import niquests
>>> r = niquests.get('https://one.one.one.one')
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf-8'
>>> r.oheaders.content_type.charset
'utf-8'
>>> r.encoding
'utf-8'
>>> r.text
'{"authenticated": true, ...'
>>> r.json()
{'authenticated': True, ...}
>>> r
<Response HTTP/2 [200]>
>>> r.ocsp_verified
True
>>> r.conn_info.established_latency
datetime.timedelta(microseconds=38)
```
or using async/await!
```python
import niquests
import asyncio

async def main() -> None:
    r = await niquests.aget('https://one.one.one.one', stream=True)
    print(r)  # Output: <Response HTTP/2 [200]>
    payload = await r.text  # we await text because we set `stream=True`!
    print(payload)  # Output: <html>...
    # or... without stream=True
    r = await niquests.aget('https://one.one.one.one')
    print(r)  # Output: <Response HTTP/3 [200]>
    payload = r.text  # we don't need to away anything, it's already loaded!
    print(payload)  # Output: <html>...

asyncio.run(main())
```

Niquests allows you to send HTTP requests extremely easily. There’s no need to manually add query strings to your URLs, or to form-encode your `PUT` & `POST` data — just use the `json` method!

[![PyPI Downloads](https://static.pepy.tech/badge/niquests/month)](https://pepy.tech/projects/niquests?timeRange=threeMonths&category=version&includeCIDownloads=true&granularity=daily&viewType=line&versions=3.*)
[![Supported Versions](https://img.shields.io/pypi/pyversions/niquests.svg)](https://pypi.org/project/niquests)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/9950/badge)](https://www.bestpractices.dev/projects/9950)

This project does not require any compilation toolchain. The HTTP/3 support is not enforced and installed if your platform can support it natively _(e.g. pre-built wheel available)_.

## ✨ Installing Niquests and Supported Versions

Niquests is available on PyPI:

```console
$ python -m pip install niquests
```

Niquests officially supports Python or PyPy 3.7+.

## 🚀 Supported Features & Best–Practices

Niquests is ready for the demands of building scalable, robust and reliable HTTP–speaking applications.

- DNS over HTTPS, DNS over QUIC, DNS over TLS, and DNS over UDP
- Automatic Content Decompression and Decoding
- OS truststore by default, no more certifi!
- OCSP Certificate Revocation Verification
- Advanced connection timings inspection
- In-memory certificates (CAs, and mTLS)
- Browser-style TLS/SSL Verification
- Certificate Revocation List (CRL)
- Sessions with Cookie Persistence
- Keep-Alive & Connection Pooling
- International Domains and URLs
- Automatic honoring of `.netrc`
- Basic & Digest Authentication
- Familiar `dict`–like Cookies
- Network settings fine-tuning
- HTTP/2 with prior knowledge
- Object-oriented headers
- Multi-part File Uploads
- Post-Quantum Security
- Chunked HTTP Requests
- Fully type-annotated!
- SOCKS Proxy Support
- Connection Timeouts
- Streaming Downloads
- HTTP/2 by default
- HTTP/3 over QUIC
- Early Responses
- Happy Eyeballs
- Multiplexed!
- Thread-safe!
- WebSocket!
- Trailers!
- DNSSEC!
- Async!
- SSE!

Need something more? Create an issue, we listen.

## 📝 Why did we pursue this?

For many years now, **Requests** has been frozen. Being left in a vegetative state and not evolving, this blocked millions of developers from using more advanced features.

We don't have to reinvent the wheel all over again, HTTP client **Requests** is well established and
really pleasant in its usage. We believe that **Requests** has the most inclusive and developer friendly interfaces.
We intend to keep it that way. As long as we can, long live Niquests!

How about a nice refresher with a mere `CTRL+H` _import requests_ **to** _import niquests as requests_ ?

## 💼 For Enterprise

Professional support for Niquests is available as part of the [Tidelift
Subscription](https://tidelift.com/subscription/pkg/pypi-niquests?utm_source=pypi-niquests&utm_medium=readme). Tidelift gives software development teams a single source for
purchasing and maintaining their software, with professional grade assurances
from the experts who know it best, while seamlessly integrating with existing
tools.

You may also be interested in unlocking specific advantages _(like access to a private issue tracker)_ by looking at our [GitHub sponsor tiers](https://github.com/sponsors/Ousret).

---

Niquests is a highly improved HTTP client that is based (forked) on Requests. The previous project original author is Kenneth Reitz and actually left the maintenance of Requests years ago.

[^1]: aiohttp was conceived solely for an asynchronous context.
[^2]: requests has no support for asynchronous request.
[^3]: while the HTTP/2 connection object can handle concurrent requests, you cannot leverage its true potential.
[^4]: loading client certificate without file can't be done.
[^5]: httpx officially claim to be thread safe but recent tests demonstrate otherwise as of february 2024. https://github.com/jawah/niquests/issues/83#issuecomment-1956065258 https://github.com/encode/httpx/issues/3072 https://github.com/encode/httpx/issues/3002 and only recently acknowledged the issue in https://github.com/encode/httpx/issues/3324 (one year after getting valid reports).
[^6]: they do not expose anything to control network aspects such as IPv4/IPv6 toggles, and timings (e.g. DNS response time, established delay, TLS handshake delay, etc...) and such.
[^7]: while advertised as possible, they refuse to make it the default due to performance issues. as of October 2024 an extra is required to enable it manually.
[^8]: they don't support HTTP/3 at all.
[^9]: you must use a custom DNS resolver so that it can preemptively connect using HTTP/3 over QUIC when remote is compatible.
[^10]: performance measured when leveraging a multiplexed connection with or without uses of any form of concurrency as of October 2024. The research compared `httpx`, `requests`, `aiohttp` against `niquests`. See https://github.com/Ousret/niquests-stats
[^11]: enabled when using a custom DNS resolver.
[^12]: available only when using HTTP/3 over QUIC and that the remote server support also the same post-quantum key-exchange algorithm. Also, the `qh3` installed version must be >= 1.1.
[^13]: most servers out there are not ready for this feature, but Niquests is already compliant and future-proof! [Caddy](https://github.com/caddyserver/caddy/releases/tag/v2.9.0) server and [HAProxy](https://github.com/haproxy/haproxy) support this!
[^14]: they don't offer any built-in to speak with a WebSocket server.

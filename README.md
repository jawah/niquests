<div align="center">
    <img src="https://user-images.githubusercontent.com/9326700/282852138-160f32e9-e6cf-495f-b39d-99891602acf9.png" alt="Niquests Logo"/>
</div>

**Niquests** is a simple, yet elegant, HTTP library. It is a drop-in replacement for **Requests**, which is under feature freeze. ✨ **Were you used to betamax, requests-mock, responses, ...?** [See how they still work! We got you covered.](https://niquests.readthedocs.io/en/latest/community/extensions.html)

<div align="center">
    <table>
        <tr>
            <td valign="middle">
                <h3>Live Benchmark</h3>
                <b>Target:</b> <code>https://httpbingo.org/get</code><br/>
                <a href="https://gist.github.com/Ousret/9e99b07e66eec48ccea5811775ec116d"><b>Conditions:</b></a> <i>All default parameters, one shared session, everything simultaneously.</i><br/>
                <b>HTTP/2</b> when supported.
            </td>
            <td>
                <img src="https://i.postimg.cc/CLxGykJL/niquests.gif" width="500" alt="Niquests Benchmark"/>
            </td>
        </tr>
    </table>
</div>


```pycon
>>> import niquests
>>> r = niquests.get('https://httpbingo.org/get', params={'hello': 'world'}, timeout=10)
>>> r.raise_for_status()
>>> r.status_code
200
>>> r.headers['content-type']
'application/json; charset=utf-8'
>>> r.json()['args']
{'hello': ['world']}
```

The same request using async/await:

```python
import asyncio

import niquests


async def main() -> None:
    async with niquests.AsyncSession() as session:
        r = await session.get(
            'https://httpbingo.org/get', params={'hello': 'world'}, timeout=10
        )
        r.raise_for_status()
        print(r.json()['args'])  # {'hello': ['world']}


asyncio.run(main())
```

Use `params=` for query parameters, `data=` for form fields, and `json=` for JSON request bodies. Call `response.json()` to decode a JSON response.

[![PyPI Downloads](https://static.pepy.tech/badge/niquests/month)](https://pepy.tech/projects/niquests?timeRange=threeMonths&category=version&includeCIDownloads=true&granularity=daily&viewType=line&versions=3.*)
[![Supported Versions](https://img.shields.io/pypi/pyversions/niquests.svg)](https://pypi.org/project/niquests)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/9950/badge)](https://www.bestpractices.dev/projects/9950)

This project does not require any compilation toolchain. The HTTP/3 support is not enforced and installed if your platform can support it natively _(e.g. pre-built wheel available)_.

## ✨ Installing Niquests and Supported Versions

Niquests is available on PyPI:

```console
$ python -m pip install niquests
```

Niquests officially supports Python or PyPy 3.7+. Even WASI or Pyodide!

## 🚀 Supported Features & Best–Practices

Niquests is ready for the demands of building scalable, robust and reliable HTTP–speaking applications.

- [DNS over HTTPS, DNS over QUIC, DNS over TLS, and DNS over UDP](https://niquests.readthedocs.io/en/latest/user/quickstart.html#dns-resolution)
- Automatic Content Decompression and Decoding
- [OS truststore by default, no more certifi!](https://niquests.readthedocs.io/en/latest/user/advanced.html#ca-certificates)
- [OCSP Certificate Revocation Verification](https://niquests.readthedocs.io/en/latest/user/advanced.html#ocsp-and-certificate-revocation)
- [Advanced connection timings inspection](https://niquests.readthedocs.io/en/latest/user/advanced.html#inspect-network-timings)
- [In-memory certificates (CAs, and mTLS)](https://niquests.readthedocs.io/en/latest/user/advanced.html#in-memory-certificates)
- [Browser-style TLS/SSL Verification](https://niquests.readthedocs.io/en/latest/user/advanced.html#tls-certificate-verification)
- Certificate Revocation List (CRL)
- Sessions with Cookie Persistence
- Keep-Alive & Connection Pooling
- International Domains and URLs
- Automatic honoring of `.netrc`
- Basic & Digest Authentication
- Familiar `dict`–like Cookies
- Network settings fine-tuning
- [HTTP/2 with prior knowledge](https://niquests.readthedocs.io/en/latest/user/advanced.html#http-2-with-prior-knowledge)
- Browser TLS Impersonator
- [Object-oriented headers](https://niquests.readthedocs.io/en/latest/api.html#niquests.Response.oheaders)
- Multi-part File Uploads
- [Swappable TLS Backend](https://niquests.readthedocs.io/en/latest/user/advanced.html#alternative-tls-backend)
- Post-Quantum Security
- Chunked HTTP Requests
- Fully type-annotated!
- [Run in the Browser!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#running-in-the-browser-pyodide)
- [SOCKS Proxy Support](https://niquests.readthedocs.io/en/latest/user/advanced.html#socks)
- [Connection Timeouts](https://niquests.readthedocs.io/en/latest/user/quickstart.html#timeouts)
- [Streaming Downloads](https://niquests.readthedocs.io/en/latest/user/advanced.html#body-content-workflow)
- HTTP/2 by default
- [HTTP/3 over QUIC](https://niquests.readthedocs.io/en/latest/user/quickstart.html#http-3-over-quic)
- [Early Responses](https://niquests.readthedocs.io/en/latest/user/advanced.html#early-responses)
- [Happy Eyeballs](https://niquests.readthedocs.io/en/latest/user/quickstart.html#happy-eyeballs)
- [Multiplexed!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#lazy-responses-and-manual-scheduling)
- [Thread-safe!](https://niquests.readthedocs.io/en/latest/user/advanced.html#thread-safety)
- [WebSocket!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#websockets)
- [Trailers!](https://niquests.readthedocs.io/en/latest/user/advanced.html#http-trailers)
- DNSSEC!
- [Async!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#async-session)
- [WASI!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#running-as-a-wasi-component)
- [SSE!](https://niquests.readthedocs.io/en/latest/user/quickstart.html#server-sent-events-sse)
- [ECH!](https://niquests.readthedocs.io/en/latest/user/advanced.html#encrypted-client-hello)

Need something more? Create an issue, we **actively** listen.

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

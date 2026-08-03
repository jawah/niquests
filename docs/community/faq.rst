.. _faq:

Frequently asked questions
==========================

This part of the documentation answers common questions about Niquests.

Encoded data?
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
any other HTTP Header. See `documentation about headers <https://niquests.readthedocs.io/en/latest/user/quickstart.html#custom-headers>`_.


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

What is "urllib3.future"?
-------------------------

**urllib3.future** is an independently maintained fork of **urllib3**. Preserving
urllib3's synchronous API is a compatibility requirement, while the fork adds the
HTTP/2, HTTP/3, async, and transport capabilities required by Niquests.

.. _urllib3-future-namespace:

Why urllib3.future provides the urllib3 namespace
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Installing the default urllib3.future wheel intentionally makes this import resolve to
urllib3.future::

    import urllib3

This selection applies to the Python environment, so other packages there that import
``urllib3`` receive urllib3.future too.

Niquests is intended to remain compatible with Requests and its extension ecosystem.
Many integrations import urllib3 directly, exchange urllib3 exceptions and response
objects, or rely on type identity. A separate namespace preserves isolation but gives up
part of that compatibility. Python packaging has no standard way for one distribution to
declare itself a compatible replacement for another, so namespace selection must happen
somewhere.

.. note:: Namespace replacement is the default, not a requirement. `Cohabitation`_
   keeps upstream urllib3 and urllib3.future under separate namespaces.

We tried upstream first
^^^^^^^^^^^^^^^^^^^^^^^

Forking was not our first choice. In May 2023 we submitted an `experimental urllib3 PR
<https://github.com/urllib3/urllib3/pull/3030>`_ for HTTP/1.1, HTTP/2, and HTTP/3 outside
:mod:`http.client`. It preserved the existing backend by default while exploring an optional,
unified protocol backend.

Seth Larson was the only urllib3 maintainer to engage substantively with its architecture.
We carefully answered the concerns raised, but the central alternative-backend proposal
was never debated to a conclusion. Our `final technical report
<https://github.com/urllib3/urllib3/pull/3030#issuecomment-1594403788>`_ was acknowledged,
then received no detailed public follow-up.

The contrast became clear later that year. A similarly sized `Emscripten transport PR
<https://github.com/urllib3/urllib3/pull/3195>`_ received 60 inline comments from multiple
maintainers and merged as experimental work in nine days. That contribution deserved its
support; its reception also showed which work the project was prepared to prioritize. We
took the difference as a signal to continue independently.

Months later, upstream found urllib3.future and opened an `upstreaming request
<https://github.com/jawah/urllib3.future/issues/46>`_ before having read the project
completely, only guessing that it continued our earlier PR. In January 2024, upstream
announced a `roughly $40,000 fundraiser for HTTP/2
<https://sethmlarson.dev/urllib3-is-fundraising-for-http2-support>`_. We respect the need
to fund sustainable open source; the timeline also confirmed that waiting would not have
delivered the protocol support Niquests needed.

How compatibility is protected
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Compatibility is a release requirement, not an assumption. Changes are checked through:

- The inherited urllib3 test suite.
- The actual test suites of Requests, Niquests, botocore, boto3, Sphinx, docker-py, and
  clickhouse-connect.
- HTTP/1.1, HTTP/2, and HTTP/3 integration tests against independent Traefik and
  go-httpbin servers.
- Regular synchronization of applicable upstream bug fixes and security patches.

These checks run continuously, and downstream compatibility regressions are priority
bugs. They cannot guarantee every private integration, especially one using undocumented
internals, but they make compatibility measurable rather than aspirational.

Alternatives we considered
^^^^^^^^^^^^^^^^^^^^^^^^^^

The alternatives below are evaluated against one requirement: existing code using
``import urllib3`` should remain compatible by default.

**Contribute upstream?** We tried first, as documented above.

**Use only a separate namespace?** This is available through `Cohabitation`_, but packages
that import ``urllib3`` directly will not receive urllib3.future objects or improvements.

**Use an opt-in extra?** If one transitive dependency enables an override extra, every
package in the environment is still affected. It produces the same global result with a
false sense of local consent.

**Expose** ``inject_into_urllib3()`` **?** Runtime injection mutates :data:`sys.modules`, makes
behavior depend on import order, and hides namespace selection inside application code.

**Manipulate path precedence at runtime?** This is harder for users, IDEs, and type
checkers to inspect and reason about.

Every approach that preserves transparent ``import urllib3`` compatibility reaches the
same destination: environment-wide namespace selection. The practical question is where
that selection occurs and whether it is deterministic, inspectable, and reversible.

The default wheel uses one `inspectable .pth file
<https://github.com/jawah/urllib3.future/blob/main/urllib3_future.pth>`_ before application
imports begin. This avoids import-order-dependent patching and leaves the environment in
one deterministic state. Of the mechanisms we found that preserve compatibility by
default, it is the most transparent and auditable. Installation can opt out through
``URLLIB3_NO_OVERRIDE=1`` as described below.

**Why not emit a warning?** A warning would not repeat for every import in one interpreter,
but it would appear for every new CLI invocation, worker process, short-lived job,
container restart, and applicable subinterpreter. At scale, that becomes persistent
operational noise. It also arrives too late to offer a useful choice: namespace selection
must happen before imports and cannot safely be reversed inside the running process.

Real-world exposure
^^^^^^^^^^^^^^^^^^^

At the time of writing, `urllib3.future receives nearly two million downloads per month
<https://www.pepy.tech/projects/urllib3-future>`_. Download counts include CI and
transitive installations, so they are not unique users or proof of consent. They do show
broad real-world exposure, while reported namespace-related compatibility failures remain
rare.

Using urllib3 within Niquests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Niquests extensions should import urllib3 through Niquests::

    from niquests.packages import urllib3

This binds the extension to the implementation selected by Niquests. It also avoids an
unnecessary dependency on today's namespace mechanism if a future major release no longer
needs it.

Audit
^^^^^

The implementation and its controls are public:

- `Source and history <https://github.com/jawah/urllib3.future>`_
- `Main CI <https://github.com/jawah/urllib3.future/blob/main/.github/workflows/ci.yml>`_
- `Downstream integration CI <https://github.com/jawah/urllib3.future/blob/main/.github/workflows/integration.yml>`_
- `CodeQL <https://github.com/jawah/urllib3.future/blob/main/.github/workflows/codeql.yml>`_
- `OpenSSF Scorecard workflow <https://github.com/jawah/urllib3.future/blob/main/.github/workflows/scorecards.yml>`_
- `Changelog <https://github.com/jawah/urllib3.future/blob/main/CHANGES.rst>`_
- `Signed release artifacts and provenance <https://github.com/jawah/urllib3.future/releases>`_

.. _urllib3-future-cohabitation:

Cohabitation
~~~~~~~~~~~~

Environments that prioritize namespace isolation over maximum Requests-extension
compatibility can install both packages. Niquests then uses the ``urllib3_future`` entry
point internally, while independent ``import urllib3`` statements continue to receive
upstream urllib3.

.. tab:: pip

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 pip install niquests --no-binary urllib3-future

.. tab:: Poetry

    Configure the project, then install:

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ poetry config --local installer.no-binary urllib3-future
        $ poetry add niquests

    Or use one command:

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 POETRY_INSTALLER_NO_BINARY=urllib3-future poetry add niquests

.. tab:: PDM

    Use one command:

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 PDM_NO_BINARY=urllib3-future pdm add niquests

    Or add this to ``pyproject.toml``:

    .. code-block:: toml

        [tool.pdm.resolution]
        no-binary = "urllib3-future"

    Then:

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ pdm add niquests

.. tab:: UV

    Add this to ``pyproject.toml``:

    .. code-block:: toml

        [tool.uv]
        no-binary-package = ["urllib3-future"]

    Then:

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ uv add niquests

Niquests translates supported :class:`urllib3.Retry <urllib3.util.Retry>` and
:class:`urllib3.Timeout <urllib3.util.Timeout>` objects across
the boundary. Third-party Requests extensions that import urllib3 directly may not share
urllib3.future's types or behavior in this configuration; that is the deliberate tradeoff
for strict namespace separation.

Why are my headers are lowercased?
----------------------------------

This may come as a surprise for some of you. Until Requests-era, header keys could arrive
as they were originally sent (case-sensitive). This is possible thanks to HTTP/1.1 protocol.
Nonetheless, RFCs specifies that header keys are *case-insensible*, that's why both Requests
and Niquests ships with :class:`~niquests.structures.CaseInsensitiveDict`.

So why did we alter it then?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The answer is quite simple, we support HTTP/2, and HTTP/3 over QUIC! The newer protocols enforce
header case-insensitivity and we can only forward them as-is (lowercased).

Can we revert this behavior? Any fallback?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Yes... kind of!
Niquests ships with a nice alternative to
:class:`~niquests.structures.CaseInsensitiveDict` that is ``kiss_headers.Headers``.
You may access it through the :attr:`oheaders <niquests.Response.oheaders>` property of
your usual Response, Request and PreparedRequest.

Am I obligated to install qh3?
------------------------------

No. But by default, it could be picked for installation. You may remove it safely at the cost
of loosing HTTP/3 over QUIC and OCSP certificate revocation status.

A shortcut would be::

    $ pip uninstall qh3

.. warning:: Your site-packages is shared, do it only if you are sure nothing else is using it.

What are "pem lib" errors?
--------------------------

Ever encountered something along::

    $ SSLError: [SSL] PEM lib (_ssl.c:2532)

Yes? Usually it means that you tried to load a certificate (CA or client cert) that is malformed.

What does malformed means?
~~~~~~~~~~~~~~~~~~~~~~~~~~

Could be just a missing newline character *RC*, or wrong format like passing a DER file instead of a PEM
encoded certificate.

If none of those seems related to your situation, feel free to open an issue at https://github.com/jawah/niquests/issues

Why do HTTP/2 and HTTP/3 seem slower than HTTP/1.1?
----------------------------------------------------

A newer HTTP version does not make serial application code concurrent. If an
application submits one request, waits for and consumes its response, and only then
submits the next request, it keeps just one exchange in flight. That pattern cannot
benefit much from stream multiplexing.

For a small serial workload, cold-connection setup, protocol discovery and negotiation,
framing, and implementation overhead can outweigh any measurable gain. HTTP/2 and
HTTP/3 are most effective when a reused connection carries several independent
exchanges concurrently. They also provide benefits beyond concurrency, including header
compression and, with HTTP/3, avoiding transport-level head-of-line blocking between
streams.

Niquests supports two straightforward ways to place several requests in flight.

.. tab:: 🔀 Async Tasks

    Keep the default ``multiplexed=False`` behavior and schedule ordinary request
    coroutines concurrently with :func:`asyncio.gather`:

    .. code:: python

        import asyncio

        from niquests import AsyncSession


        async def main() -> None:
            url = "https://httpbingo.org/delay/1"

            async with AsyncSession() as session:
                requests = [session.get(url) for _ in range(10)]
                responses = await asyncio.gather(*requests)

            print([response.status_code for response in responses])


        asyncio.run(main())

    Each task waits for its own eager response, but the event loop lets the requests
    progress concurrently. With HTTP/2 or HTTP/3, the exchanges can use independent
    streams on one connection. HTTP/1.1 can also benefit by using multiple pooled
    connections, so an improvement here demonstrates concurrency rather than proving
    that one protocol is inherently faster.

.. tab:: 🔂 Sync Lazy Responses

    In synchronous code, enable lazy responses with ``multiplexed=True``. Submit every
    request before resolving any response:

    .. code:: python

        from niquests import Session


        url = "https://httpbingo.org/delay/1"

        with Session(multiplexed=True) as session:
            responses = [session.get(url) for _ in range(10)]

            session.gather(*responses)
            print([response.status_code for response in responses])

    The option name is historical: ``multiplexed=True`` does not enable HTTP/2 or
    HTTP/3 and does not alter protocol negotiation. It returns lazy, promise-backed
    responses so multiple requests can be submitted before synchronous code waits for
    their results.

.. warning:: Do not inspect a lazy response inside the submission loop. Accessing
   :attr:`~niquests.Response.status_code`, headers, or body data resolves that response immediately and can
   serialize the workload again. Submit all requests first, then call
   :meth:`~niquests.Session.gather` or inspect the responses.

Do not confuse :func:`asyncio.gather` with
:meth:`AsyncSession.gather <niquests.AsyncSession.gather>`. :func:`asyncio.gather`
schedules ordinary async request coroutines concurrently.
:meth:`AsyncSession.gather <niquests.AsyncSession.gather>`
resolves lazy responses and has an effect only when the session was created with
``multiplexed=True``.

These examples demonstrate scheduling patterns, not a protocol benchmark. For a useful
HTTP-version comparison:

- Reuse a session and decide whether cold-connection setup belongs in the measurement.
- Verify the negotiated protocol through :attr:`Response.http_version
  <niquests.Response.http_version>`; HTTP/3 discovery may occur after an initial request.
- Use equivalent concurrency and consume every response body in each test.
- Account for DNS, TLS, QUIC discovery, ``Alt-Svc``, server limits, and network variance.
- Repeat the measurement instead of drawing conclusions from a single run.

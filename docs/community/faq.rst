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

It is a fork of the well-known **urllib3** library. Niquests would not have been
able to deliver its feature set on top of the existing **urllib3** library.

**urllib3.future** is independent, managed separately, and fully compatible with
its counterpart (API-wise).

Shadow-Naming
~~~~~~~~~~~~~

Your environment may or may not include the legacy urllib3 package in addition to urllib3.future.
So doing::

    import urllib3

By default, it will be ``urllib3-future`` sitting there.

.. note:: This behavior is not mandatory. You can circumvent it with a simple command. See below (Cohabitation).

The first reaction is usually instinctive: *software should not silently replace other software in my environment.*
That feels like a firm principle - and a reasonable one.

But then the question becomes: what's the alternative?

**Contributing upstream?** That was attempted. A pull request bringing HTTP/2 support to urllib3 sat without review for months. The door wasn't open for our proposal.

**A separate namespace?** Over 100 packages call ``import urllib3`` directly in their source code. Forking the entire ecosystem isn't viable.

**An opt-in extra, like** ``pip install urllib3-future[override]`` **?** If any single dependency in the tree activates it, every other package in the environment is affected. Same outcome, false sense of consent.

**A public** ``inject_into_urllib3()`` **function?** That's a ``sys.modules`` hack hiding inside application code, triggered by import order, invisible unless you go hunting for it. Strictly worse.

**Why not a warning printed out to stderr?** This was considered, but printing a warning on every import would pollute stderr in ways that quickly become untenable.
Long-running applications, CI pipelines, and containerized services would accumulate massive volumes of repeated warnings, one for every process, every worker, every restart.
In sub-interpreter environments, each subinterpreter would emit its own copy of the warning, multiplying the noise further.
Many monitoring and logging systems treat unexpected stderr output as a signal that something is wrong, which would generate false alerts at scale.
A warning also creates the worst middle ground: it doesn't prevent the override from happening, it doesn't give the user a mechanism to act on it inline, and it
trains developers to ignore it, the same fatigue that makes deprecation warnings invisible after the first occurrence.

*Every path leads to the same destination.* The only difference is where the redirection happens and how easy it is to find. The ``.pth`` approach we implemented is deterministic - it runs before
any user code, lives in one inspectable file in ``site-packages``, and supports a clean opt-out via ``URLLIB3_NO_OVERRIDE=1`` at install time. Of all the options, it's the most transparent.

The discomfort is understandable. But it assumes a packaging system that supports package replacement natively - and Python's doesn't.
When the principle collides with a hard ecosystem constraint, pragmatism has to win. Especially when the pragmatic choice is also the most auditable one.

What tends to happen in practice is this: once the override is understood, most developers choose to keep it.

The HTTP/2 and HTTP/3 support alone justifies it, and the compatibility story - we actually run the actual test suites of Requests, botocore, boto3, Sphinx, docker-py, and others on
every push on top of urllib3-future, this builds genuine confidence that nothing will break.

Using urllib3 within Niquests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using Niquests alongside urllib3-future, prefer importing urllib3 through Niquests
rather than directly::

    from niquests.packages import urllib3

This ensures smoother upgrades in the future when important changes are made.

Audit
^^^^^

Anyone can freely analyze urllib3-future, its practices, sources, workflows ci/cd, sigstore signature, and so on.
More details about the project history and more advanced topics are directly addressed there.

Visit https://github.com/jawah/urllib3.future

Cohabitation
~~~~~~~~~~~~

You may have both urllib3 and urllib3.future installed if wished.
Niquests will use the secondary entrypoint for urllib3.future internally.

.. tab:: pip

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 pip install niquests --no-binary urllib3-future

.. tab:: Poetry

    Option 1)

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ poetry config --local installer.no-binary urllib3-future
        $ poetry add niquests

    Option 2)

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 POETRY_INSTALLER_NO_BINARY=urllib3-future poetry add niquests

.. tab:: PDM

    Option 1)

    .. code-block::

        $ URLLIB3_NO_OVERRIDE=1 PDM_NO_BINARY=urllib3-future pdm add niquests

    Option 2) Add to your pyproject.toml metadata

    .. code-block:: toml

        [tool.pdm.resolution]
        no-binary = "urllib3-future"

    Then:

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ pdm add niquests

.. tab:: UV

    Add to your pyproject.toml metadata

    .. code-block:: toml

        [tool.uv]
        no-binary-package = ["urllib3-future"]

    Then:

    .. code-block::

        $ export URLLIB3_NO_OVERRIDE=1
        $ uv add niquests

It does not change anything for you. You may still pass ``urllib3.Retry`` and
``urllib3.Timeout`` regardless of the cohabitation, Niquests will do
the translation internally.

.. warning:: Separate namespace for urllib3 and urllib3-future can disturb the backward compatibility with Requests, especially with 3rd party plugins/extensions. Feel free to open an issue if you encounter compatibility bugs.

Why are my headers are lowercased?
----------------------------------

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

Why HTTP/2 and HTTP/3 seems slower than HTTP/1.1?
-------------------------------------------------

Because you are not leveraging its potential properly. Most of the time, developers tend to
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

.. note:: This piece of code demonstrate how to emit concurrent requests in a synchronous context without threads and async.

We would gladly discuss potential implementations if needed, just open a new issue at https://github.com/jawah/niquests/issues

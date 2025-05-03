.. _migrate:

Requests → Niquests Guide
=========================

If you're reading this, you're probably interested in Niquests. We're thrilled to have
you onboard.

This section will cover two use cases:

- I am a developer that regularly drive Requests
- I am a library maintainer that depend on Requests

Developer migration
-------------------

Niquests aims to be as compatible as possible with Requests, and that is
with confidence that you can migrate to Niquests without breaking changes.

.. code:: python

    import requests
    requests.get(...)

Would turn into either

.. code:: python

    import niquests
    niquests.get(...)

Or simply

.. code:: python

    import niquests as requests
    requests.get(...)

.. tip:: If you were used to use ``urllib3.Timeout`` or ``urllib3.Retry`` you can either keep them as-is or use our fully compatible ``niquests.RetryConfiguration`` or ``niquests.TimeoutConfiguration`` instead.

If you were used to depends on urllib3.

.. code:: python

    from urllib3 import Timeout
    import requests

Will now become:

.. code:: python

    import niquests
    from niquests.packages.urllib3 import Timeout

.. note:: urllib3 is safely aliased as ``niquests.packages.urllib3``. Using the alias provided by Niquests is safer.

Maintainer migration
--------------------

In order to migrate your library with confidence, you'll have to also adjust your tests.
The library itself (sources) should be really easy to migrate (cf. developer migration)
but the tests may be harder to adapt.

The main reason behind this difficulty is often related to a strong tie with third-party
mocking library such as ``responses``.

To overcome this, we will introduce you to a clever bypass. If you are using pytest, do the
following in your ``conftest.py``, see https://docs.pytest.org/en/6.2.x/fixture.html#conftest-py-sharing-fixtures-across-multiple-files
for more information. (The goal would simply to execute the following piece of code before the tests)

.. code:: python

    from sys import modules

    import niquests
    import requests
    from niquests.packages import urllib3

    # the mock utility 'response' only works with 'requests'
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.compat"] = requests.compat
    modules["requests.packages.urllib3"] = urllib3

.. warning:: This code sample is only to be executed in a development environment, it permit to fool the third-party dependencies that have a strong tie on Requests.

.. warning:: Some pytest plugins may load/import Requests at startup.
    Disable the plugin auto-loading first by either passing ``PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`` (in environment)
    or ``pytest -p "no:pytest-betamax"`` in CLI parameters. Replace ``pytest-betamax`` by the name of the target plugin.
    To find out the name of the plugin auto-loaded, execute ``pytest --trace-config`` as the name aren't usually what
    you would expect them to be.

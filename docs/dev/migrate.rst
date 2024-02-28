.. _migrate:

Migration Guide
================

If you're reading this, you're probably interested in Niquests. We're thrilled to have
you onboard.

This section will cover two use cases:

- I am a developer that regularly drive Requests
- I am a library maintainer that depend on Requests

Developer migration
-------------------

Niquests aims to be as compatible as possible with Requests, and that is
with confidence that you can migrate to Niquests without breaking changes.

::

    import requests
    requests.get(...)

Would turn into either

::

    import niquests
    niquests.get(...)

Or simply

::

    import niquests as requests
    requests.get(...)


Maintainer migration
--------------------

In order to migrate your library with confidence, you'll have to also adjust your tests.
The library itself (sources) should be really easy to migrate (cf. developer migration)
but the tests may be harder to adapt.

The main reason behind this difficulty is often related to a strong tie with third-party
mocking library such as ``response``.

To overcome this, we will introduce you to a clever bypass. If you are using pytest, do the
following in your ``conftest.py``, see https://docs.pytest.org/en/6.2.x/fixture.html#conftest-py-sharing-fixtures-across-multiple-files
for more information. (The goal would simply to execute the following piece of code before the tests)

::

    from sys import modules

    import niquests
    import urllib3

    # the mock utility 'response' only works with 'requests'
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.packages.urllib3"] = urllib3

.. warning:: This code sample is only to be executed in a development environment, it permit to fool the third-party dependencies that have a strong tie on Requests.

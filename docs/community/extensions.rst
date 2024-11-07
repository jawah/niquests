Extensions from Requests to Niquests
====================================

One of the main strength behind Requests is the wide range of community plugins / extensions that
allows one to extend its abilities.

In this chapter, we'll look into some of the most populars extensions and see how you can use it with Niquests
instead of Requests.

There is 4 levels of compatibility:

- Native: No adjustment are required, should work as-is out of the box.
- Working: A minor tweak is required that does not harm your environment at all.
- Usable: A consequent patch may be required, usually assigning / injecting Niquests module impersonating Requests.
- Unusable: You cannot use the plugin due to various reasons. Usually the library leverage private properties or excessively rely on broken behaviors that are now patched in Niquests.

.. warning:: Sometimes, plugin/packages explicitly require Requests as a dependency, thus making your environment heavier, sometime for no reason. No solution exist to override this behavior.

.. note:: Feel free to reach out to the maintainers and speak up about Niquests. Suggesting a patch to support both Requests, and Niquests is really straightforward!

Requests Cache
--------------

.. note:: Classified as: Working

`requests-cache`_ is a persistent HTTP cache that provides an easy way to get better performance with the python requests library.

.. _requests-cache: https://github.com/requests-cache/requests-cache

Quickstart to leverage its potential::

    import requests_cache
    import niquests


    class CacheSession(requests_cache.session.CacheMixin, niquests.Session):
        ...


    if __name__ == "__main__":

        s = CacheSession()

        for i in range(60):
            r = s.get('https://httpbin.org/delay/1')

responses
---------

.. note:: Classified as: Usable

Apply the following code to your ``conftest.py``::

    from sys import modules

    import requests
    import niquests
    import urllib3

    # responses is tied to Requests
    # and Niquests is entirely compatible with it.
    # we can fool it without effort.
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.models"] = niquests.models
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.packages.urllib3"] = urllib3

betamax
-------

.. note:: Classified as: Usable

Apply the following code to your ``conftest.py``::

    from sys import modules

    import requests
    import niquests
    import urllib3

    # betamax is tied to Requests
    # and Niquests is almost entirely compatible with it.
    # we can fool it without effort.
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.models"] = niquests.models
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.packages.urllib3"] = urllib3

    # niquests no longer have a compat submodule
    # but betamax need it. no worries, as betamax
    # explicitly need requests, we'll give it to him.
    modules["requests.compat"] = requests.compat

    # doing the import now will make betamax working with Niquests!
    # no extra effort.
    import betamax

    # the base mock does not implement close(), which is required
    # for our HTTP client. No biggy.
    betamax.mock_response.MockHTTPResponse.close = lambda _: None

And make sure that the betamax plugin isn't loaded at boot with (pyproject.toml)::

    [tool.pytest.ini_options]
    # this avoids pytest loading betamax+Requests at boot.
    # this allows us to patch betamax and makes it use Niquests instead.
    addopts = "-p no:pytest-betamax"

Or run pytest directly with ``pytest -p no:pytest-betamax``.

Requests-Toolbelt
-----------------

.. note:: Classified as: Usable

`Requests-Toolbelt`_ is a collection of utilities that some users of Niquests may desire,
but do not belong in Niquests proper. This library is actively maintained
by members of the Requests core team, and reflects the functionality most
requested by users within the community.

.. _Requests-Toolbelt: https://toolbelt.readthedocs.io/en/latest/index.html

requests-aws4auth
-----------------

.. note:: Classified as: Native

requests-file
-------------

.. note:: Classified as: Usable

requests-mock
-------------

.. note:: Classified as: Usable

You will need to create a fixture to override the default bind to Requests in ``conftest.py`` like so::

    import niquests as requests

    @pytest.fixture(scope='function')
    def patched_requests_mock():
        """This is required because pytest load plugins at boot, way before conftest.
        The only reliable way to make requests_mock use Niquests is to customize it after."""
        import requests_mock  # noqa: E402

        class _WrappedMocker(requests_mock.Mocker):
            """Ensure requests_mock work with the drop-in replacement Niquests!"""

            def __init__(self, session=None, **kwargs):
                # we purposely skip invoking super() to avoid the strict typecheck on session.
                self._mock_target = session or requests.Session
                self.case_sensitive = kwargs.pop('case_sensitive', self.case_sensitive)
                self._adapter = (
                    kwargs.pop('adapter', None)
                    or requests_mock.adapter.Adapter(case_sensitive=self.case_sensitive)
                )

                self._json_encoder = kwargs.pop('json_encoder', None)
                self.real_http = kwargs.pop('real_http', False)
                self._last_send = None

                if kwargs:
                    raise TypeError('Unexpected Arguments: %s' % ', '.join(kwargs))

            def request(self, *args, **kwargs):
                if "headers" not in kwargs:
                    kwargs["headers"] = {}
                if "json" in kwargs and kwargs["json"] is not None:
                    kwargs["headers"]["Content-Type"] = "application/json"
                return self.register_uri(*args, **kwargs)

        with _WrappedMocker() as m:
            yield m

Then, use it as you were used to::

    def test_sometime(patched_requests_mock):
        patched_requests_mock.get("https://example.com/", text="hello world")

requests-ntlm
-------------

.. note:: Classified as: Native

requests-unixsocket
-------------------

.. note:: Classified as: Usable

requests-futures
----------------

.. warning:: Classified as: Unusable

This project is no longer required for you! Niquests ships with native asyncio support.
Furthermore, you may leverage multiplexing to optimize your HTTP calls at will.

requests-kerberos
-----------------

.. note:: Classified as: Native

Nothing change from your previous code::

    >>> import niquests
    >>> from requests_kerberos import HTTPKerberosAuth
    >>> r = niquests.get("http://example.org", auth=HTTPKerberosAuth())

The ``HTTPKerberosAuth`` can be used natively without patch.

requests-pkcs12
---------------

.. note:: Classified as: Native

requests-ntlm3
--------------

.. note:: Classified as: Native

requests-gssapi
---------------

.. note:: Classified as: Native

Requests-OAuthlib
-----------------

.. note:: Classified as: Working

`requests-oauthlib`_ makes it possible to do the OAuth dance from Niquests
automatically. This is useful for the large number of websites that use OAuth
to provide authentication. It also provides a lot of tweaks that handle ways
that specific OAuth providers differ from the standard specifications.

.. _requests-oauthlib: https://requests-oauthlib.readthedocs.io/en/latest/

Please patch your program as follow::

    import niquests
    from oauthlib.oauth2 import BackendApplicationClient
    import requests_oauthlib

    requests_oauthlib.OAuth2Session.__bases__ = (niquests.Session,)

    client_id = "xxxxxxxxxxxxxxxxxxxxxxxxxxx"
    client_secret = "xxxxxxxxxxxxxxxxxxxxxxxxxxx"
    token_url = 'https://api.github.com/token'

    if __name__ == "__main__":
        client = BackendApplicationClient(client_id=client_id)
        sample = requests_oauthlib.OAuth2Session(client=client)

        token = sample.fetch_token(token_url, client_secret=client_secret)

The key element to be considered is ``requests_oauthlib.OAuth2Session.__bases__ = (niquests.Session,)``.
You may apply it to ``requests_oauthlib.OAuth1Session`` too.


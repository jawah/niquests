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

.. warning:: Be advised that this extension nullify the advantage of using ``multiplexed=True`` within your Session constructor as is eagerly access the content.

responses
---------

.. note:: Classified as: Usable

Apply the following code to your ``conftest.py``::

    from sys import modules

    import requests
    import niquests
    from niquests.packages import urllib3

    # responses is tied to Requests
    # and Niquests is entirely compatible with it.
    # we can fool it without effort.
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.models"] = niquests.models
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.packages.urllib3"] = urllib3

If you want to extend Responses to support mocking asynchronous calls, you will
have to extend the bellow code with the following::

    # make 'responses' mock both sync and async
    # 'Requests' ever only supported sync
    # Fortunately interfaces are mirrored in 'Niquests'
    import responses  # noqa: E402


    class NiquestsMock(responses.RequestsMock):
        """Asynchronous support for responses"""

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(
                *args,
                target="niquests.adapters.HTTPAdapter.send",
                **kwargs,
            )

            self._patcher_async = None

        def unbound_on_async_send(self):
            async def send(
                adapter: "niquests.adapters.AsyncHTTPAdapter",
                request: "niquests.PreparedRequest",
                *args: typing.Any,
                **kwargs: typing.Any,
            ) -> "niquests.Response":
                if args:
                    # that probably means that the request was sent from the custom adapter
                    # It is fully legit to send positional args from adapter, although,
                    # `requests` implementation does it always with kwargs
                    # See for more info: https://github.com/getsentry/responses/issues/642
                    try:
                        kwargs["stream"] = args[0]
                        kwargs["timeout"] = args[1]
                        kwargs["verify"] = args[2]
                        kwargs["cert"] = args[3]
                        kwargs["proxies"] = args[4]
                    except IndexError:
                        # not all kwargs are required
                        pass

                resp = self._on_request(adapter, request, **kwargs)

                if kwargs["stream"]:
                    return resp

                resp.__class__ = niquests.Response
                return resp

            return send

        def unbound_on_send(self):
            def send(
                adapter: "niquests.adapters.HTTPAdapter",
                request: "niquests.PreparedRequest",
                *args: typing.Any,
                **kwargs: typing.Any,
            ) -> "niquests.Response":
                if args:
                    # that probably means that the request was sent from the custom adapter
                    # It is fully legit to send positional args from adapter, although,
                    # `requests` implementation does it always with kwargs
                    # See for more info: https://github.com/getsentry/responses/issues/642
                    try:
                        kwargs["stream"] = args[0]
                        kwargs["timeout"] = args[1]
                        kwargs["verify"] = args[2]
                        kwargs["cert"] = args[3]
                        kwargs["proxies"] = args[4]
                    except IndexError:
                        # not all kwargs are required
                        pass

                return self._on_request(adapter, request, **kwargs)

            return send

        def start(self) -> None:
            if self._patcher:
                # we must not override value of the _patcher if already applied
                # this prevents issues when one decorated function is called from
                # another decorated function
                return

            self._patcher = std_mock.patch(target=self.target, new=self.unbound_on_send())
            self._patcher_async = std_mock.patch(
                target=self.target.replace("HTTPAdapter", "AsyncHTTPAdapter"),
                new=self.unbound_on_async_send()
            )

            self._patcher.start()
            self._patcher_async.start()

        def stop(self, allow_assert: bool = True) -> None:
            if self._patcher:
                # prevent stopping unstarted patchers
                self._patcher.stop()
                self._patcher_async.stop()

                # once patcher is stopped, clean it. This is required to create a new
                # fresh patcher on self.start()
                self._patcher = None
                self._patcher_async = None

            if not self.assert_all_requests_are_fired:
                return

            if not allow_assert:
                return

            not_called = [m for m in self.registered() if m.call_count == 0]
            if not_called:
                raise AssertionError(
                    "Not all requests have been executed {!r}".format(
                        [(match.method, match.url) for match in not_called]
                    )
                )


    mock = _default_mock = NiquestsMock(assert_all_requests_are_fired=False)

    setattr(responses, "mock", mock)
    setattr(responses, "_default_mock", _default_mock)

    for kw in [
        "activate",
        "add",
        "_add_from_file",
        "add_callback",
        "add_passthru",
        "assert_call_count",
        "calls",
        "delete",
        "DELETE",
        "get",
        "GET",
        "head",
        "HEAD",
        "options",
        "OPTIONS",
        "patch",
        "PATCH",
        "post",
        "POST",
        "put",
        "PUT",
        "registered",
        "remove",
        "replace",
        "reset",
        "response_callback",
        "start",
        "stop",
        "upsert",
    ]:
        if not hasattr(responses, kw):
            continue
        setattr(responses, kw, getattr(mock, kw))


This will automatically make Responses work seamlessly when using awaitable http calls.

betamax
-------

.. note:: Classified as: Usable

Apply the following code to your ``conftest.py``::

    from sys import modules

    import requests
    import niquests
    import niquests.packages import urllib3

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

    from sys import modules

    import requests
    import niquests
    from niquests.packages import urllib3

    # impersonate Requests!
    modules["requests"] = niquests
    modules["requests.adapters"] = niquests.adapters
    modules["requests.models"] = niquests.models
    modules["requests.exceptions"] = niquests.exceptions
    modules["requests.packages.urllib3"] = urllib3
    modules["requests.compat"] = requests.compat

    @pytest.fixture(scope='function')
    def patched_requests_mock():
        """This is required because pytest load plugins at boot, way before conftest.
        The only reliable way to make requests_mock use Niquests is to customize it after."""
        import requests_mock  # noqa: E402

        class _WrappedMocker(requests_mock.Mocker):
            """Ensure requests_mock work with the drop-in replacement Niquests!"""

            def __init__(self, session=None, **kwargs):
                # we purposely skip invoking super() to avoid the strict typecheck on session.
                self._mock_target = session or niquests.Session
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

.. warning:: This extension load/import Requests at pytest startup.
    Disable the plugin auto-loading first by either passing ``PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`` (in environment)
    or ``pytest -p "no:requests_mock"`` in CLI parameters. You may also append ``-p "no:requests_mock"`` in addopts
    of your pyproject.toml or equivalent.

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


.. _recommended:

Recommended Packages and Extensions
===================================

Niquests is compatible with a great variety of powerful and useful third-party extensions.
This page provides an overview of some of the best of them.

CacheControl
------------

`CacheControl`_ is an extension that adds a full HTTP cache to Niquests. This
makes your web requests substantially more efficient, and should be used
whenever you're making a lot of web niquests.

.. _CacheControl: https://cachecontrol.readthedocs.io/en/latest/

Requests-Toolbelt
-----------------

`Requests-Toolbelt`_ is a collection of utilities that some users of Niquests may desire,
but do not belong in Niquests proper. This library is actively maintained
by members of the Requests core team, and reflects the functionality most
requested by users within the community.

.. _Requests-Toolbelt: https://toolbelt.readthedocs.io/en/latest/index.html

.. warning:: Requests-Toolbelt actually require Requests as a dependency thus making you have duplicate dependencies.

Requests-OAuthlib
-----------------

`requests-oauthlib`_ makes it possible to do the OAuth dance from Niquests
automatically. This is useful for the large number of websites that use OAuth
to provide authentication. It also provides a lot of tweaks that handle ways
that specific OAuth providers differ from the standard specifications.

.. _requests-oauthlib: https://requests-oauthlib.readthedocs.io/en/latest/

.. warning:: There's a catch when trying to use Niquests with `requests-oauthlib`_. You will need a quick patch prior to using it.

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
You may apply it to `requests_oauthlib.OAuth1Session` too.

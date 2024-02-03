.. _authentication:

Authentication
==============

This document discusses using various kinds of authentication with Niquests.

Many web services require authentication, and there are many different types.
Below, we outline various forms of authentication available in Niquests, from
the simple to the complex.


Basic Authentication
--------------------

Many web services that require authentication accept HTTP Basic Auth. This is
the simplest kind, and Niquests supports it straight out of the box.

Making requests with HTTP Basic Auth is very simple::

    >>> from niquests.auth import HTTPBasicAuth
    >>> basic = HTTPBasicAuth('user', 'pass')
    >>> niquests.get('https://httpbin.org/basic-auth/user/pass', auth=basic)
    <Response HTTP/2 [200]>

In fact, HTTP Basic Auth is so common that Niquests provides a handy shorthand
for using it::

    >>> niquests.get('https://httpbin.org/basic-auth/user/pass', auth=('user', 'pass'))
    <Response HTTP/2 [200]>

Providing the credentials in a tuple like this is exactly the same as the
``HTTPBasicAuth`` example above.

For DNS
~~~~~~~

Doing basic authorization using for DNS over HTTPS resolver can be done easily.
You must provide the user and pass into the DNS url as such::

    from niquests import Session

    with Session(resolver="doh://user:pass@my-resolver.tld") as s:
        resp = s.get("https://pie.dev/get")

Passing a bearer token
----------------------

You may use ``auth=my_token`` as a shortcut to passing ``headers={"Authorization": f"Bearer {my_token}"}`` in
get, post, request, etc...

.. note:: If you pass a token with its custom prefix, it will be taken and passed as-is. e.g. ``auth="NotBearer eyDdx.."``

For DNS
~~~~~~~

Doing a bearer token using for DNS over HTTPS resolver can be done easily.
You must provide the token directly into the DNS url as such::

    from niquests import Session

    with Session(resolver="doh://token@my-resolver.tld") as s:
        resp = s.get("https://pie.dev/get")

netrc Authentication
~~~~~~~~~~~~~~~~~~~~

If no authentication method is given with the ``auth`` argument and the
Authorization header has not been set, Niquests will attempt to get the
authentication credentials for the URL's hostname from the user's netrc file.

If credentials for the hostname are found, the request is sent with HTTP Basic
Auth.


Digest Authentication
---------------------

Another very popular form of HTTP Authentication is Digest Authentication,
and Niquests supports this out of the box as well::

    >>> from niquests.auth import HTTPDigestAuth
    >>> url = 'https://httpbin.org/digest-auth/auth/user/pass'
    >>> niquests.get(url, auth=HTTPDigestAuth('user', 'pass'))
    <Response HTTP/2 [200]>


OAuth 1 Authentication
----------------------

A common form of authentication for several web APIs is OAuth. The ``requests-oauthlib``
library allows Niquests users to easily make OAuth 1 authenticated requests::

    >>> import niquests
    >>> from requests_oauthlib import OAuth1

    >>> url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
    >>> auth = OAuth1('YOUR_APP_KEY', 'YOUR_APP_SECRET',
    ...               'USER_OAUTH_TOKEN', 'USER_OAUTH_TOKEN_SECRET')

    >>> niquests.get(url, auth=auth)
    <Response HTTP/2 [200]>

For more information on how to OAuth flow works, please see the official `OAuth`_ website.
For examples and documentation on requests-oauthlib, please see the `requests_oauthlib`_
repository on GitHub

OAuth 2 and OpenID Connect Authentication
-----------------------------------------

The ``requests-oauthlib`` library also handles OAuth 2, the authentication mechanism
underpinning OpenID Connect. See the `requests-oauthlib OAuth2 documentation`_ for
details of the various OAuth 2 credential management flows:

* `Web Application Flow`_
* `Mobile Application Flow`_
* `Legacy Application Flow`_
* `Backend Application Flow`_

Other Authentication
--------------------

Niquests is designed to allow other forms of authentication to be easily and
quickly plugged in. Members of the open-source community frequently write
authentication handlers for more complicated or less commonly-used forms of
authentication. Some of the best have been brought together under the
`Requests organization`_, including:

- Kerberos_
- NTLM_

If you want to use any of these forms of authentication, go straight to their
GitHub page and follow the instructions.


New Forms of Authentication
---------------------------

If you can't find a good implementation of the form of authentication you
want, you can implement it yourself. Niquests makes it easy to add your own
forms of authentication.

To do so, subclass :class:`AuthBase <niquests.auth.AuthBase>` and implement the
``__call__()`` method::

    >>> import niquests
    >>> class MyAuth(niquests.auth.AuthBase):
    ...     def __call__(self, r):
    ...         # Implement my authentication
    ...         return r
    ...
    >>> url = 'https://httpbin.org/get'
    >>> niquests.get(url, auth=MyAuth())
    <Response HTTP/2 [200]>

When an authentication handler is attached to a request,
it is called during request setup. The ``__call__`` method must therefore do
whatever is required to make the authentication work. Some forms of
authentication will additionally add hooks to provide further functionality.

Further examples can be found under the `Requests organization`_ and in the
``auth.py`` file.

.. _OAuth: https://oauth.net/
.. _requests_oauthlib: https://github.com/requests/requests-oauthlib
.. _requests-oauthlib OAuth2 documentation: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html
.. _Web Application Flow: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#web-application-flow
.. _Mobile Application Flow: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#mobile-application-flow
.. _Legacy Application Flow: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#legacy-application-flow
.. _Backend Application Flow: https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html#backend-application-flow
.. _Kerberos: https://github.com/requests/requests-kerberos
.. _NTLM: https://github.com/requests/requests-ntlm
.. _Requests organization: https://github.com/requests

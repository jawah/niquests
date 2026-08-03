.. meta::
   :description: Classes, functions, and methods API documentation for Python Niquests. Session, AsyncSession, synchronous and asynchronous request helpers, Response, configuration, and exceptions.
   :keywords: Python Niquests API, API Docs Niquests, Requests API, Session, AsyncSession, request, get, options, head, post, put, patch, delete, query, async http, TLSConfiguration, Timeout, ConnectionError, TooManyRedirects, Response, AsyncResponse

.. _api:

Developer interface
===================

.. module:: niquests

This part of the documentation covers Niquests' public interfaces. Where
Niquests depends on external libraries, we document the most important parts
here and provide links to the canonical documentation.


Main interface
--------------

Niquests provides synchronous and asynchronous convenience functions for its
supported HTTP methods. Synchronous functions return a :class:`Response
<Response>`. Awaited asynchronous functions return a :class:`Response
<Response>`, or an :class:`AsyncResponse <AsyncResponse>` when streaming.

.. autofunction:: request
.. autofunction:: arequest

.. autofunction:: get
.. autofunction:: aget
.. autofunction:: options
.. autofunction:: aoptions
.. autofunction:: head
.. autofunction:: ahead
.. autofunction:: post
.. autofunction:: apost
.. autofunction:: put
.. autofunction:: aput
.. autofunction:: patch
.. autofunction:: apatch
.. autofunction:: delete
.. autofunction:: adelete
.. autofunction:: query
.. autofunction:: aquery

Exceptions
----------

.. autoexception:: niquests.RequestException
.. autoexception:: niquests.ConnectionError
.. autoexception:: niquests.exceptions.SSLError
.. autoexception:: niquests.HTTPError
.. autoexception:: niquests.URLRequired
.. autoexception:: niquests.TooManyRedirects
.. autoexception:: niquests.ConnectTimeout
.. autoexception:: niquests.ReadTimeout
.. autoexception:: niquests.Timeout
.. autoexception:: niquests.JSONDecodeError


Request sessions
----------------

.. _sessionapi:

.. autoclass:: Session
   :inherited-members:

.. autoclass:: AsyncSession
   :inherited-members:

Lower-level classes
-------------------

.. autoclass:: niquests.Request
   :inherited-members:

.. py:class:: niquests.structures.CaseInsensitiveDict

   A mutable mapping that preserves keys while comparing them case-insensitively.

.. autoclass:: Response
   :inherited-members:

.. autoclass:: AsyncResponse
   :inherited-members:

.. warning::

   An :class:`AsyncResponse <niquests.AsyncResponse>` is returned only in asynchronous
   mode when you specify ``stream=True``. Otherwise, expect a
   :class:`Response <niquests.Response>` instance.

.. autoclass:: RetryConfiguration
   :inherited-members:

.. autoclass:: TimeoutConfiguration
   :inherited-members:

Configuration and reference types
---------------------------------

.. autoclass:: TLSConfiguration
   :inherited-members:

.. autoclass:: RevocationConfiguration
   :inherited-members:

.. autoclass:: RevocationStrategy
   :inherited-members:

.. autoclass:: niquests.models.TransferProgress
   :inherited-members:

Type aliases
------------

Reusable annotations for request values, hooks, resolvers, and gateway applications are
available from :mod:`niquests.typing`.

Request values
~~~~~~~~~~~~~~

.. autodata:: niquests.typing.HttpMethodType
.. autodata:: niquests.typing.QueryParameterType
.. autodata:: niquests.typing.BodyFormType
.. autodata:: niquests.typing.BodyType
.. autodata:: niquests.typing.AsyncBodyType
.. autodata:: niquests.typing.JSONEncoderType
.. autodata:: niquests.typing.HeadersType
.. autodata:: niquests.typing.CookiesType
.. autodata:: niquests.typing.TLSVerifyType
.. autodata:: niquests.typing.TLSClientCertType
.. autodata:: niquests.typing.TimeoutType
.. autodata:: niquests.typing.HttpAuthenticationType
.. autodata:: niquests.typing.AsyncHttpAuthenticationType
.. autodata:: niquests.typing.ProxyType
.. autodata:: niquests.typing.RetryType

File uploads
~~~~~~~~~~~~

.. autodata:: niquests.typing.BodyFileType
.. autodata:: niquests.typing.MultiPartFileType
.. autodata:: niquests.typing.MultiPartFilesType
.. autodata:: niquests.typing.MultiPartFilesAltType

Hooks
~~~~~

.. autodata:: niquests.typing.HookCallableType
.. autodata:: niquests.typing.HookType
.. autodata:: niquests.typing.AsyncHookCallableType
.. autodata:: niquests.typing.AsyncHookType

Resolvers
~~~~~~~~~

.. autodata:: niquests.typing.ResolverType
.. autodata:: niquests.typing.AsyncResolverType

Gateway applications
~~~~~~~~~~~~~~~~~~~~

.. autodata:: niquests.typing.ASGIScope
.. autodata:: niquests.typing.ASGIMessage
.. autodata:: niquests.typing.ASGIReceive
.. autodata:: niquests.typing.ASGISend
.. autodata:: niquests.typing.ASGIApp
.. autodata:: niquests.typing.WSGIStartResponse
.. autodata:: niquests.typing.WSGIApp

Lower-lower-level classes
-------------------------

.. autoclass:: niquests.PreparedRequest
   :inherited-members:

.. autoclass:: niquests.adapters.BaseAdapter
   :inherited-members:

.. autoclass:: niquests.adapters.HTTPAdapter
   :inherited-members:

.. autoclass:: niquests.adapters.AsyncBaseAdapter
   :inherited-members:

.. autoclass:: niquests.adapters.AsyncHTTPAdapter
   :inherited-members:

Hooks and middleware
--------------------

.. autoclass:: niquests.hooks.LifeCycleHook
   :members: pre_request, pre_send, on_upload, early_response, response
   :no-index:

.. autoclass:: niquests.hooks.AsyncLifeCycleHook
   :members: pre_request, pre_send, on_upload, early_response, response
   :no-index:

.. autoclass:: niquests.LeakyBucketLimiter
   :members: __init__

.. autoclass:: niquests.AsyncLeakyBucketLimiter
   :members: __init__

.. autoclass:: niquests.TokenBucketLimiter
   :members: __init__

.. autoclass:: niquests.AsyncTokenBucketLimiter
   :members: __init__

Authentication
--------------

.. autoclass:: niquests.auth.AuthBase
.. autoclass:: niquests.auth.HTTPBasicAuth
.. autoclass:: niquests.auth.HTTPProxyAuth
.. autoclass:: niquests.auth.HTTPDigestAuth

.. autoclass:: niquests.auth.AsyncAuthBase
.. autoclass:: niquests.auth.AsyncHTTPDigestAuth

.. _api-cookies:

Cookies
-------

.. autofunction:: niquests.utils.dict_from_cookiejar
.. autofunction:: niquests.utils.add_dict_to_cookiejar
.. autofunction:: niquests.cookies.cookiejar_from_dict

.. autoclass:: niquests.cookies.RequestsCookieJar
   :inherited-members:

.. autoclass:: niquests.cookies.CookieConflictError
   :inherited-members:



Status code lookup
------------------

.. autoclass:: niquests.codes

.. automodule:: niquests.status_codes


Migrating to 3.x
----------------

Compared with the 2.0 release, there were relatively few backwards
incompatible changes, but there are still a few issues to be aware of with
this major release.


Removed
~~~~~~~

* Property ``apparent_encoding`` in favor of a discrete internal inference.
* Support for the legacy ``chardet`` detector when it was present in the environment.
  Extra ``chardet_on_py3`` is now unavailable.
* Deprecated function ``get_encodings_from_content`` from utils.
* Deprecated function ``get_unicode_from_response`` from utils.
* BasicAuth middleware support for username and password types other than :class:`bytes` or :class:`str`.
* The **ISO-8859-1** charset fallback when the content type is text and no charset was specified.
* Mixin classes ``RequestEncodingMixin`` and ``RequestHooksMixin`` due to OOP violations. Their behavior now resides directly in the child classes.
* Function ``unicode_is_ascii`` as it is part of the stable :class:`str` stdlib on Python 3 or greater.
* Alias function ``session`` for :class:`Session <niquests.Session>` context manager that was kept for BC reasons since the v1.
* pyOpenSSL/urllib3 injection when the built-in :mod:`ssl` module lacks SNI support, because every supported interpreter now provides it.
* Constant ``DEFAULT_CA_BUNDLE_PATH``, and submodule ``certs`` due to dropping ``certifi``.
* Function ``extract_zipped_paths`` because rendered useless as it was made to handle an edge case where ``certifi`` is "zipped".
* Extra ``security`` when installing this package. It was previously emptied in the previous major.
* Warning emitted when passing a file opened in text-mode instead of binary. urllib3.future can overrule
  the content-length if it detects an error. You should not encounter broken request being sent.
* Support for ``simplejson`` when it was present in the environment.
* Submodule ``compat``.
* Dependency check at runtime for ``urllib3``. There's no more check and warnings at runtime for that subject. Ever.

Behavioural changes
~~~~~~~~~~~~~~~~~~~

* Niquests negotiates an HTTP/2 connection by default and falls back to HTTP/1.1 if HTTP/2 is unavailable.
* HTTP/3 support can be available by default if your platform supports the pre-built wheel for qh3.
* Server capability for HTTP/3 is remembered automatically (in-memory) for subsequent requests.

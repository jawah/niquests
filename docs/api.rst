.. _api:

Developer Interface
===================

.. module:: niquests

This part of the documentation covers all the interfaces of Niquests. For
parts where Niquests depends on external libraries, we document the most
important right here and provide links to the canonical documentation.


Main Interface
--------------

All of Niquests' functionality can be accessed by these 7 methods.
They all return an instance of the :class:`Response <Response>` object.

.. autofunction:: request

.. autofunction:: head
.. autofunction:: get
.. autofunction:: post
.. autofunction:: put
.. autofunction:: patch
.. autofunction:: delete

Exceptions
----------

.. autoexception:: niquests.RequestException
.. autoexception:: niquests.ConnectionError
.. autoexception:: niquests.HTTPError
.. autoexception:: niquests.URLRequired
.. autoexception:: niquests.TooManyRedirects
.. autoexception:: niquests.ConnectTimeout
.. autoexception:: niquests.ReadTimeout
.. autoexception:: niquests.Timeout
.. autoexception:: niquests.JSONDecodeError


Request Sessions
----------------

.. _sessionapi:

.. autoclass:: Session
   :inherited-members:


Lower-Level Classes
-------------------

.. autoclass:: niquests.Request
   :inherited-members:

.. autoclass:: Response
   :inherited-members:


Lower-Lower-Level Classes
-------------------------

.. autoclass:: niquests.PreparedRequest
   :inherited-members:

.. autoclass:: niquests.adapters.BaseAdapter
   :inherited-members:

.. autoclass:: niquests.adapters.HTTPAdapter
   :inherited-members:

Authentication
--------------

.. autoclass:: niquests.auth.AuthBase
.. autoclass:: niquests.auth.HTTPBasicAuth
.. autoclass:: niquests.auth.HTTPProxyAuth
.. autoclass:: niquests.auth.HTTPDigestAuth

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



Status Code Lookup
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
* Support for the legacy ``chardet`` detector in case it was present in environment.
  Extra ``chardet_on_py3`` is now unavailable.
* **requests.compat** no longer hold reference to _chardet_.
* Deprecated ``requests.packages`` that was meant to avoid breakage from people importing ``urllib3`` or ``chardet`` within this package.
  They were _vendored_ in early versions of Requests. A long time ago.
* Deprecated function ``get_encodings_from_content`` from utils.
* Deprecated function ``get_unicode_from_response`` from utils.
* BasicAuth middleware no-longer support anything else than ``bytes`` or ``str`` for username and password.
* ``requests.compat`` is stripped of every reference that no longer vary between supported interpreter version.
* Charset fall back **ISO-8859-1** when content-type is text and no charset was specified.
* Main function ``get``, ``post``, ``put``, ``patch``, ``delete``, and ``head`` no longer accept **kwargs**. They have a fixed list of typed argument.
  It is no longer possible to specify non-supported additional keyword argument from a ``Session`` instance or directly through ``requests.api`` functions.
  e.g. function ``delete`` no-longer accept ``json``, or ``files`` arguments. as per RFCs specifications. You can still override this behavior through the ``request`` function.
* Mixin classes ``RequestEncodingMixin``, and ``RequestHooksMixin`` due to OOP violations. Now deported directly into child classes.
* Function ``unicode_is_ascii`` as it is part of the stable ``str`` stdlib on Python 3 or greater.
* Alias function ``session`` for ``Session`` context manager that was kept for BC reasons since the v1.
* pyOpenSSL/urllib3 injection in case built-in ssl module does not have SNI support as it is not the case anymore for every supported interpreters.
* Constant ``DEFAULT_CA_BUNDLE_PATH``, and submodule ``certs`` due to dropping ``certifi``.
* Function ``extract_zipped_paths`` because rendered useless as it was made to handle an edge case where ``certifi`` is "zipped".
* Extra ``security`` when installing this package. It was previously emptied in the previous major.
* Warning emitted when passing a file opened in text-mode instead of binary. urllib3.future can overrule
  the content-length if it detects an error. You should not encounter broken request being sent.
* Support for ``simplejson`` if was present in environment.
* Submodule ``compat``.
* Dependency check at runtime for ``urllib3``. There's no more check and warnings at runtime for that subject. Ever.

Behavioural Changes
~~~~~~~~~~~~~~~~~~~

* Niquests negotiate for a HTTP/2 connection by default, fallback to HTTP/1.1 if not available.
* Support for HTTP/3 can be present by default if your platform support the pre-built wheel for qh3.
* Server capability for HTTP/3 is remembered automatically (in-memory) for subsequent requests.

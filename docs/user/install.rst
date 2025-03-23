.. meta::
   :description: Fast track to install Niquests and support latest protocols and security features. Install via pip, uv or poetry immediately! Discover available and most used optional extensions like zstandard, brotli, and WebSocket support.
   :keywords: Install Requests Python, Pip http client, Uv http install, Uv http client, Pip Niquests, Uv Niquests, Python WebSocket, SOCKS proxy, proxy

.. _install:

Installation of Niquests
========================

This part of the documentation covers the installation of Niquests.
The first step to using any software package is getting it properly installed.


$ Install!
----------

To install Niquests, simply run this simple command in your terminal of choice::

    $ python -m pip install niquests


Dependencies
~~~~~~~~~~~~

Niquests has currently 3 mandatory dependencies.

- **wassima**
  - This package allows Niquests a seamless access to your native OS trust store. It avoids to rely on ``certify``.
- **urllib3-future**
  - The direct and immediate replacement for the well known ``urllib3`` package. Serve as the Niquests core.
- **charset-normalizer**
  - A clever encoding detector that helps provide a smooth user experience when dealing with legacy resources.

*urllib3-future* itself depends on three other dependencies. Two of them are installed everytime (mandatory).

- **h11**
  - A state-machine to speak HTTP/1.1
- **jh2**
  - A state-machine to speak HTTP/2
- **qh3**
  - A QUIC stack with a HTTP/3 state-machine

.. note::
    **qh3** may not be installed on your machine even if **urllib3-future** depends on it.
    That dependency is BOTH required AND optional.
    There's a lot of markers in the requirement definition to prevent someone to accidentally try compile the source.
    **qh3** is not pure Python and ship a ton of prebuilt wheels, but unfortunately it is
    impossible to ship every possible combination of system/architecture.
    e.g. this is why doing ``pip install niquests`` on a riscv linux distro will NOT bring **qh3**. but will for arm64, i686 or x86_64.

.. warning::
    Depending on your environment and installation order you could be surprised that ``urllib3-future`` replaces
    ``urllib3`` in your environment. Fear not, as this package was perfectly designed to allows the best
    backward-compatibility possible for end-users.
    Installing Niquests affect other packages, as they will use ``urllib3-future`` instead of ``urllib3``.
    The prevalent changes are as follow: No longer using HTTP/1 by default, not depending on ``http.client``, can
    negotiate HTTP/2, and HTTP/3, backward compatible with old Python and OpenSSL, not opinionated on other SSL backend,
    and finally faster. This list isn't exhaustive. Any issues encountered regarding this cohabitation will be handled
    at https://github.com/jawah/urllib3.future with the utmost priority. Find deeper rational in the exposed repository.

.. note::
    Doing a ``pip install --force-reinstall urllib3`` will restore the legacy urllib3 in a flash if needed.
    At the cost of loosing the perfect backward compatibility with third party plugins (using Niquests).

Extras
~~~~~~

Niquests come with a few extras that requires you to install the package with a specifier.

- **ws**

To benefit from the integrated WebSocket experience, you may install Niquests as follow::

    $ python -m pip install niquests[ws]

- **socks**

SOCKS proxies can be used in Niquests, at the sole condition to have::

    $ python -m pip install niquests[socks]

- **Brotli**, **Zstandard** (zstd) and **orjson**

Niquests can run significantly faster when your environment is capable of decompressing Brotli, and Zstd.
Also, we took the liberty to allows using the alternative json decoder ``orjson`` that is faster than the
standard json library.

To immediately benefit from this, run::

    $ python -m pip install niquests[speedups]

.. note:: You may at your own discretion choose multiple options such as ``pip install niquests[socks,ws]``.

.. note:: You can install every optionals by running ``pip install niquests[full]``.

If you don't want ``orjson`` to be present and only zstd for example, run::

    $ python -m pip install niquests[zstd]

- **http3** or/and **ocsp**

As explained higher in this section, our HTTP/3 implementation depends on you having ``qh3`` installed. And it may not
be the case depending on your environment.

To force install ``qh3`` run the installation using::

    $ python -m pip install niquests[http3]


.. note:: ``ocsp`` extra is a mere alias of ``http3``. Our OCSP client depends on **qh3** inners anyway.

- **full**

If by any chance you wanted to get the full list of (extra) features, you may install Niquests with::

    $ python -m pip install niquests[full]

Instead of joining the long list of extras like ``zstd,socks,ws`` for example.

Get the Source Code
-------------------

Niquests is actively developed on GitHub, where the code is
`always available <https://github.com/jawah/niquests>`_.

You can either clone the public repository::

    $ git clone https://github.com/jawah/niquests.git

Or, download the `tarball <https://github.com/jawah/niquests/tarball/main>`_::

    $ curl -OL https://github.com/jawah/niquests/tarball/main
    # optionally, zipball is also available (for Windows users).

Once you have a copy of the source, you can embed it in your own Python
package, or install it into your site-packages easily::

    $ cd niquests
    $ python -m pip install .

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
  - The direct and immediate replacement for the well known :mod:`urllib3` package. Serve as the Niquests core.
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
    **qh3** is a conditional dependency of **urllib3-future**. Its environment markers
    cover platforms with supported prebuilt wheels so a normal installation does not
    unexpectedly compile the native extension from source. It is impossible to publish
    wheels for every operating system and architecture.

    For example, the current markers include Linux RISC-V, AArch64, i686, and x86_64,
    but omit Linux LoongArch64, FreeBSD, and NetBSD. On those omitted platforms,
    ``pip install niquests`` does not request **qh3** by default. The ``http3`` extra
    requests it explicitly and may therefore attempt a source build.

.. warning::
    Installing Niquests also installs ``urllib3-future``. Its default wheel
    intentionally makes ``import urllib3`` resolve to urllib3.future. This selection
    applies to the Python environment, so other packages there that import
    :mod:`urllib3` receive urllib3.future too.

    This default preserves compatibility with Requests integrations that import
    urllib3 directly or exchange its objects. See
    :ref:`urllib3-future-namespace` for the complete rationale, compatibility controls,
    alternatives considered, and audit links.

.. note::
    Namespace replacement is the default, not a requirement. You can keep upstream
    :mod:`urllib3` and urllib3.future under separate namespaces. See
    :ref:`urllib3-future-cohabitation` for pip, Poetry, PDM, and uv instructions.

Extras
~~~~~~

Niquests come with a few extras that requires you to install the package with a specifier.

- **ws**

To benefit from the integrated WebSocket experience, you may install Niquests as follow::

    $ python -m pip install niquests[ws]

- **socks**

SOCKS proxies can be used in Niquests, at the sole condition to have::

    $ python -m pip install niquests[socks]

- **rtls**

Immediately swap your OpenSSL/LibreSSL default for a state-of-the-art, and memory-safe Rustls backend::

    $ python -m pip install niquests[rtls]

- **utls**

Immediately swap your OpenSSL/LibreSSL default for a known BoringSSL backend, used by major player like Google Chrome::

    $ python -m pip install niquests[utls]

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

.. note:: **full** does not include ``utls``.

Get the source code
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

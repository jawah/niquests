.. _install:

Installation of Niquests
========================

This part of the documentation covers the installation of Niquests.
The first step to using any software package is getting it properly installed.


$ python -m pip install niquests
--------------------------------

To install Niquests, simply run this simple command in your terminal of choice::

    $ python -m pip install niquests

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

.. _faq:

Frequently Asked Questions
==========================

This part of the documentation answers common questions about Niquests.

Encoded Data?
-------------

Niquests automatically decompresses gzip-encoded responses, and does
its best to decode response content to unicode when possible.

When either the `brotli <https://pypi.org/project/Brotli/>`_ or `brotlicffi <https://pypi.org/project/brotlicffi/>`_
package is installed, requests also decodes Brotli-encoded responses.

You can get direct access to the raw response (and even the socket),
if needed as well.


Custom User-Agents?
-------------------

Niquests allows you to easily override User-Agent strings, along with
any other HTTP Header. See `documentation about headers <https://niquests.readthedocs.io/en/latest/user/quickstart/#custom-headers>`_.


What are "hostname doesn't match" errors?
-----------------------------------------

These errors occur when :ref:`SSL certificate verification <verification>`
fails to match the certificate the server responds with to the hostname
Niquests thinks it's contacting. If you're certain the server's SSL setup is
correct (for example, because you can visit the site with your browser).

`Server-Name-Indication`_, or SNI, is an official extension to SSL where the
client tells the server what hostname it is contacting. This is important
when servers are using `Virtual Hosting`_. When such servers are hosting
more than one SSL site they need to be able to return the appropriate
certificate based on the hostname the client is connecting to.

Python 3 already includes native support for SNI in their SSL modules.

.. _`Server-Name-Indication`: https://en.wikipedia.org/wiki/Server_Name_Indication
.. _`virtual hosting`: https://en.wikipedia.org/wiki/Virtual_hosting

"""
requests.compat
~~~~~~~~~~~~~~~

This module previously handled import compatibility issues
between Python 2 and Python 3. It remains for backwards
compatibility until the next major version.
"""

# json/simplejson module import resolution
try:
    import simplejson as json  # type: ignore[import]
    from simplejson import JSONDecodeError
except ImportError:
    import json
    from json import JSONDecodeError

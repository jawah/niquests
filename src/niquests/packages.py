from __future__ import annotations

import sys
import typing

from ._compat import HAS_LEGACY_URLLIB3

# just to enable smooth type-completion!
if typing.TYPE_CHECKING:
    if HAS_LEGACY_URLLIB3:
        import urllib3_future as urllib3  # noqa
    else:
        import urllib3  # type: ignore[no-redef]  # noqa

    import charset_normalizer as chardet  # noqa

    charset_normalizer = chardet  # noqa

    import idna  # type: ignore[import-not-found]  # noqa

# This code exists for backwards compatibility reasons.
# I don't like it either. Just look the other way. :)
for package in (
    "urllib3",
    "charset_normalizer",
    "idna",
    "chardet",
):
    try:
        locals()[package] = __import__(package if package != "chardet" else "charset_normalizer")
    except ImportError:
        continue

    # This traversal is apparently necessary such that the identities are
    # preserved (requests.packages.urllib3.* is urllib3.*)
    for mod in list(sys.modules):
        if mod == package or mod.startswith(f"{package}."):
            sys.modules[f"niquests.packages.{mod}"] = sys.modules[mod]

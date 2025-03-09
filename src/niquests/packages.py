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
    to_be_imported: str = package

    if package == "chardet":
        to_be_imported = "charset_normalizer"
    elif package == "urllib3" and HAS_LEGACY_URLLIB3:
        to_be_imported = "urllib3_future"

    try:
        locals()[package] = __import__(to_be_imported)
    except ImportError:
        continue  # idna could be missing. not required!

    # This traversal is apparently necessary such that the identities are
    # preserved (requests.packages.urllib3.* is urllib3.*)
    for mod in list(sys.modules):
        if mod == to_be_imported or mod.startswith(f"{to_be_imported}."):
            inner_mod = mod

            if HAS_LEGACY_URLLIB3 and inner_mod == "urllib3_future" or inner_mod.startswith("urllib3_future."):
                inner_mod = inner_mod.replace("urllib3_future", "urllib3")
            elif inner_mod == "charset_normalizer":
                inner_mod = "chardet"

            try:
                sys.modules[f"niquests.packages.{inner_mod}"] = sys.modules[mod]
            except KeyError:
                continue

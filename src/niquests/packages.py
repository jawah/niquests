from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import typing

from ._compat import HAS_LEGACY_URLLIB3

# just to enable smooth type-completion!
if typing.TYPE_CHECKING:
    import charset_normalizer as chardet
    import urllib3

    charset_normalizer = chardet

    import idna  # type: ignore[import-not-found]

# Mapping of aliased package prefixes:
#   "niquests.packages.<alias>." to "<real-package>."
# Populated by the loop below, consumed by the import hook.
_ALIAS_TO_REAL: dict[str, str] = {}

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

    # Determine the alias prefix (what niquests code imports)
    # and the real prefix (the actual installed package).
    if package == "chardet":
        alias_prefix = "niquests.packages.chardet."
        real_prefix = "charset_normalizer."
        alias_root = "niquests.packages.chardet"
        real_root = "charset_normalizer"
    elif package == "urllib3" and HAS_LEGACY_URLLIB3:
        alias_prefix = "niquests.packages.urllib3."
        real_prefix = "urllib3_future."
        alias_root = "niquests.packages.urllib3"
        real_root = "urllib3_future"
    else:
        alias_prefix = f"niquests.packages.{package}."
        real_prefix = f"{package}."
        alias_root = f"niquests.packages.{package}"
        real_root = package

    _ALIAS_TO_REAL[alias_prefix] = real_prefix
    _ALIAS_TO_REAL[alias_root] = real_root

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


class _AliasModuleLoader(importlib.abc.Loader):
    """A loader that imports the real module and hands it back for the alias name.

    The real import MUST happen here and not in find_spec: the import
    machinery invokes meta path finders while holding the interpreter-wide
    import lock. See https://github.com/jawah/niquests/issues/415
    """

    def __init__(self, real_name: str, alias_root: str, real_root: str) -> None:
        self._real_name = real_name
        self._alias_root = alias_root
        self._real_root = real_root

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> typing.Any:
        real_module = importlib.import_module(self._real_name)

        # Adjust the alias spec before the import machinery initializes the
        # (real) module attributes with it.
        spec.origin = getattr(real_module, "__file__", None)
        if hasattr(real_module, "__path__"):
            spec.submodule_search_locations = list(real_module.__path__)
        else:
            spec.submodule_search_locations = None

        # Eagerly alias every submodule of the real package loaded so far,
        # this avoid duplicate refs for same target.
        real_root_dot = self._real_root + "."
        for mod_name in list(sys.modules):
            if mod_name == self._real_root or mod_name.startswith(real_root_dot):
                alias_mod_name = self._alias_root + mod_name[len(self._real_root) :]
                if alias_mod_name not in sys.modules:
                    try:
                        sys.modules[alias_mod_name] = sys.modules[mod_name]
                    except KeyError:
                        continue

        # _load_unlocked/module_from_spec reuse this module object for the
        # alias instead of creating (and executing) a blank one.
        return real_module

    def exec_module(self, module: typing.Any) -> None:
        pass


class _NiquestsPackagesAliasImporter(importlib.abc.MetaPathFinder):
    """Made to avoid duplicate due to lazy imports at urllib3-future side(...)"""

    def find_spec(
        self,
        fullname: str,
        path: typing.Any = None,
        target: typing.Any = None,
    ) -> importlib.machinery.ModuleSpec | None:
        # The actual import is deferred to _AliasModuleLoader.create_module.
        real_name: str | None = None
        alias_root: str | None = None
        real_root: str | None = None

        for alias, real in _ALIAS_TO_REAL.items():
            if fullname == alias or fullname.startswith(alias if alias.endswith(".") else alias + "."):
                real_name = real + fullname[len(alias) :]
                alias_root = alias.rstrip(".")
                real_root = real.rstrip(".")
                break

        if real_name is None or alias_root is None or real_root is None:
            return None

        # The spec is deliberately created without knowing whether the target
        # is a package.
        return importlib.machinery.ModuleSpec(
            fullname,
            _AliasModuleLoader(real_name, alias_root, real_root),
        )


# Insert at front so we intercept before the default PathFinder.
sys.meta_path.insert(0, _NiquestsPackagesAliasImporter())


__all__ = (
    "urllib3",
    "chardet",
    "charset_normalizer",
    "idna",
)

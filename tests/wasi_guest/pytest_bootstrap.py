from __future__ import annotations

import importlib
import pkgutil

import _pytest
import packaging
import pluggy


def prepare_pytest() -> None:
    # pluggy 1.7 resolves this lazily from distribution metadata. Freeze the
    # installed version while that metadata is available during componentization.
    pluggy.__version__ = pluggy.__version__

    # componentize-py only bundles modules imported during pre-initialization.
    for package in (_pytest, packaging):
        for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
            try:
                importlib.import_module(module.name)
            except ImportError:
                pass

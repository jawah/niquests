from __future__ import annotations

import encodings.unicode_escape  # noqa: F401
import importlib
import os
import pkgutil

import _pytest
import packaging
import pytest
from coverage_runner import new_coverage, save_coverage
from wit_world import exports

_import_coverage = new_coverage()
_import_coverage.start()

# componentize-py only bundles modules imported during pre-initialization.
for package in (_pytest, packaging):
    for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
        try:
            importlib.import_module(module.name)
        except ImportError:
            pass

import niquests  # noqa: E402,F401
import niquests.extensions.wasi  # noqa: E402,F401

_import_coverage.stop()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


class Run(exports.Run):
    def run(self) -> None:
        os.chdir("/artifacts")
        coverage = new_coverage(".coverage.wasi.sync")
        coverage.start()
        os.chdir("/workspace")
        try:
            result = pytest.main(
                [
                    "-v",
                    "-s",
                    "-c",
                    "/dev/null",
                    "-p",
                    "no:cacheprovider",
                    "-p",
                    "no:faulthandler",
                    "-p",
                    "no:debugging",
                    "-p",
                    "no:doctest",
                    "--confcutdir=/workspace/tests/wasi_guest/sync",
                    "/workspace/tests/wasi_guest/sync",
                ]
            )
        finally:
            coverage.stop()
            save_coverage(coverage, _import_coverage)
        if result != 0:
            raise RuntimeError(f"pytest exited with status {result}")

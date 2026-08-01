from __future__ import annotations

import encodings.unicode_escape  # noqa: F401
import importlib
import os
import pkgutil
import sys

import _pytest
import packaging
import pytest  # noqa: F401
from coverage_runner import new_coverage, save_coverage
from wit_world import exports

_import_coverage = new_coverage()
_import_coverage.start()

for package in (_pytest, packaging):
    for module in pkgutil.walk_packages(package.__path__, f"{package.__name__}."):
        try:
            importlib.import_module(module.name)
        except ImportError:
            pass

from test_wasi import CASES  # noqa: E402

import niquests  # noqa: E402, F401

_import_coverage.stop()
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"


class Run(exports.Run):
    async def run(self) -> None:
        if len(sys.argv) != 2 or sys.argv[1] not in CASES:
            raise RuntimeError(f"expected one of: {', '.join(CASES)}")
        case_id = sys.argv[1]
        os.chdir("/artifacts")
        target = os.environ.get("NIQUESTS_WASI_HTTP_TARGET")
        target_suffix = f".{target}" if target else ""
        coverage = new_coverage(f".coverage.wasi.async.{case_id}{target_suffix}")
        coverage.start()
        os.chdir("/workspace")
        try:
            await CASES[case_id]()
        finally:
            coverage.stop()
            save_coverage(coverage, _import_coverage)

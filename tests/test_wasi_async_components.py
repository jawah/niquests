from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_ARTIFACTS = os.environ.get("NIQUESTS_WASI_ARTIFACTS")
_WASMTIME = os.environ.get("NIQUESTS_WASMTIME")
_ROOT = os.environ.get("NIQUESTS_WASI_ROOT")

pytestmark = pytest.mark.skipif(
    not (_ARTIFACTS and _WASMTIME and _ROOT),
    reason="WASI components are built by the dedicated Nox session",
)

_PROFILES = {
    "async-p3": ("niquests-async-p3.wasm", ("-S", "p3,http")),
    "combined-p3": (
        "niquests-combined-p3.wasm",
        ("-Sp3", "-Shttp", "-Sinherit-network", "-Sallow-ip-name-lookup=y"),
    ),
    "hybrid-async-p3": (
        "niquests-hybrid-async-p3.wasm",
        ("-Sp3", "-Shttp", "-Sinherit-network", "-Sallow-ip-name-lookup=y"),
    ),
    "socket-async-p3": (
        "niquests-socket-async-p3.wasm",
        ("-Sp3", "-Sinherit-network", "-Sallow-ip-name-lookup=y"),
    ),
    "unavailable-async-p3": ("niquests-unavailable-async-p3.wasm", ("-Sp3",)),
}

_PROFILE_CASES = {
    "async-p3": (
        "buffered-get",
        "request-options-timeout",
        "streamed-get-and-close-before-eof",
        "incomplete-response-body",
        "gzip-raw-and-decoded",
        "retry-configuration",
        "retry-exhaustion",
        "redirect-chain-and-disabled-following",
        "307-preserves-method-and-body",
        "cookies-are-guest-managed",
        "streamed-upload-and-progress",
        "upload-failure-callback",
        "early-response-during-upload",
        "sse",
        "sse-edge-formatting",
        "websocket-is-rejected",
        "unsupported-tls-controls",
        "defensive-edges",
    ),
    "combined-p3": ("combined-world-capabilities-and-requests",),
    "hybrid-async-p3": ("hybrid-selection-and-requests",),
    "socket-async-p3": (
        "capabilities-and-adapter-selection",
        "https-http2-and-concurrency",
        "real-http2-trailers",
        "redirect-chain-and-disabled-following",
    ),
    "unavailable-async-p3": ("async-capabilities-are-unavailable",),
}
_CASES = tuple(
    (profile, case_id, target)
    for profile, case_ids in _PROFILE_CASES.items()
    for case_id in case_ids
    for target in (("local", "live") if profile == "async-p3" and case_id != "defensive-edges" else (None,))
)


@pytest.mark.parametrize(
    ("profile", "case_id", "target"),
    _CASES,
    ids=["-".join(item for item in (profile, case_id, target) if item) for profile, case_id, target in _CASES],
)
def test_async_wasi_component(profile: str, case_id: str, target: str | None, request: pytest.FixtureRequest) -> None:
    assert _ARTIFACTS is not None
    assert _WASMTIME is not None
    assert _ROOT is not None
    component_name, features = _PROFILES[profile]
    if target == "live":
        request.getfixturevalue("requires_wan")
    artifacts = Path(_ARTIFACTS)
    command = [
        _WASMTIME,
        "run",
        *features,
        "--dir",
        f"{_ROOT}::/workspace",
        "--dir",
        "/dev",
        "--dir",
        f"{artifacts}::/artifacts",
        *(["--env", f"NIQUESTS_WASI_HTTP_TARGET={target}"] if target else []),
        str(artifacts / component_name),
        case_id,
    ]
    result = subprocess.run(command, check=False)
    assert result.returncode == 0, f"Wasmtime exited with status {result.returncode}"

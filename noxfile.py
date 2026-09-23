from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import tarfile
import time
import urllib.request
from contextlib import ExitStack, contextmanager
from http.client import RemoteDisconnected
from pathlib import Path
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError

import nox


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@contextmanager
def local_revocation_services(session: nox.Session, directory: Path):
    """Keep both host services within the lifetime of the managed test stack."""
    python = session.run("python", "-c", "import sys; print(sys.executable)", silent=True).strip()
    env = dict(os.environ)
    env.update(session.env)
    commands = (
        [python, "-m", "tests.revocation.ocsp_responder", "--directory", str(directory)],
        [python, "-m", "http.server", "8891", "--bind", "127.0.0.1", "--directory", str(directory)],
    )
    with ExitStack() as cleanup:
        processes = []
        for command in commands:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                env={key: value for key, value in env.items() if value is not None},
            )
            cleanup.callback(_stop_process, process)
            processes.append(process)
        yield processes


@contextmanager
def local_http_stack(session: nox.Session, *, stop_on_exit: bool = True, with_revocation: bool = True):
    """Run the local HTTP/1.1, HTTP/2, and HTTP/3 test stack when available."""
    if os.environ.get("TRAEFIK_HTTPBIN_ENABLE", "true").lower() != "true":
        yield
        return

    root = Path.cwd()
    cert_dir = root / "traefik"
    certificate = cert_dir / "httpbin.local.pem"
    private_key = cert_dir / "httpbin.local.pem.key"
    root_ca = root / "rootCA.pem"
    if with_revocation:
        for port in (8890, 8891):
            try:
                probe = socket.create_connection(("127.0.0.1", port), timeout=0.2)
            except (ConnectionRefusedError, SocketTimeout):
                # Windows may hit the probe timeout before reporting a closed port.
                pass
            else:
                probe.close()
                session.error(f"Local revocation port {port} is already in use; stop the existing service first")

    required_certificates = (certificate, private_key, root_ca)
    certificates_changed = not all(path.is_file() for path in required_certificates)
    if certificates_changed:
        for path in required_certificates:
            if path.exists():
                path.unlink()
        session.log("Generating local Traefik certificates")
        session.run(
            "python",
            "-m",
            "trustme",
            "-i",
            "httpbin.local",
            "alt.httpbin.local",
            "localhost",
            "127.0.0.1",
            "-d",
            str(cert_dir),
        )
        (cert_dir / "server.pem").replace(certificate)
        (cert_dir / "server.key").replace(private_key)
        (cert_dir / "client.pem").replace(root_ca)

    revocation_dir = cert_dir / "revocation"
    leaves = ("good-ocsp", "revoked-ocsp", "good-crl", "revoked-crl")
    certificates = ("root", "intermediate", *leaves, "ocsp-responder")
    revocation_artifacts = (
        *(f"{name}.{suffix}" for name in certificates for suffix in ("pem", "key")),
        *(f"{name}.fullchain.pem" for name in leaves),
        "intermediate.der",
        "intermediate.crl",
    )
    # Refresh short-lived PKI for managed revocation runs. Docker-only runs still
    # need the certificates referenced by Traefik's shared configuration.
    if with_revocation or not all((revocation_dir / name).is_file() for name in revocation_artifacts):
        session.run("python", "-m", "tests.revocation.generate")
        certificates_changed = True

    is_windows = platform.system() == "Windows"
    compose_file = "docker-compose.win.yaml" if is_windows else "docker-compose.yaml"
    if is_windows:
        checkout = root / "go-httpbin"
        if not checkout.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/mccutchen/go-httpbin.git", str(checkout)],
                check=True,
            )
        shutil.copyfile(cert_dir / "patched.Dockerfile", checkout / "patched.Dockerfile")

    if (
        shutil.which("docker")
        and subprocess.run(["docker", "compose", "version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        == 0
    ):
        compose = ["docker", "compose", "-f", compose_file]
    elif not is_windows and shutil.which("docker-compose"):
        compose = ["docker-compose", "-f", compose_file]
    else:
        message = "Docker Compose is unavailable; local protocol tests will be skipped"
        if os.environ.get("CI") or session.env.get("NIQUESTS_REQUIRE_REVOCATION") == "1":
            session.error(message)
        session.warn(message)
        yield
        return

    started = False
    ready = False
    revocation_processes: list[subprocess.Popen] = []
    cleanup = ExitStack()
    try:
        for attempt in range(2):
            result = subprocess.run(
                [*compose, "up", "-d", *(("--force-recreate",) if certificates_changed else ())], check=False
            )
            if result.returncode == 0:
                started = True
                break
            if attempt == 0:
                session.warn("Docker Compose startup failed; retrying in 30 seconds")
                time.sleep(30)
        if not started:
            subprocess.run([*compose, "logs", "--tail=128"], check=False)
            message = "Docker Compose failed to start the local protocol stack"
            if os.environ.get("CI") or session.env.get("NIQUESTS_REQUIRE_REVOCATION") == "1":
                session.error(message)
            session.warn(message)
            yield
            return

        if with_revocation:
            revocation_processes = cleanup.enter_context(local_revocation_services(session, revocation_dir))

        stack_ip = os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for attempt in range(120):
            try:
                with opener.open(
                    urllib.request.Request(
                        f"http://{stack_ip}:8888/get",
                        headers={"Host": "httpbin.local"},
                    ),
                    timeout=1.0,
                ) as response:
                    if response.status == 200:
                        break
            except (HTTPError, URLError, RemoteDisconnected, TimeoutError, SocketTimeout, ConnectionError):
                pass
            if attempt == 119:
                subprocess.run([*compose, "logs", "--tail=128"], check=False)
                raise TimeoutError("Timed out waiting for the local protocol stack")
            time.sleep(1)

        if with_revocation:
            session.run("python", "-m", "tests.revocation.check", "--directory", str(revocation_dir), "--host", stack_ip)
            for process in revocation_processes:
                if process.poll() is not None:
                    raise RuntimeError(f"Local revocation service exited with status {process.returncode}: {process.args}")

        session.log("Local protocol stack is ready")
        ready = True
        yield revocation_processes
    finally:
        try:
            cleanup.close()
        finally:
            # A failed `up` can still leave partially started containers behind.
            if stop_on_exit or not ready:
                subprocess.run([*compose, "stop"], check=False)


def tests_impl(
    session: nox.Session,
    extras: str = "socks,ws",
    cohabitation: bool | None = False,
    pytest_extra_args: list[str] | None = None,
    override_dev_deps: str | None = None,
    with_revocation: bool = True,
) -> None:
    if pytest_extra_args is None:
        pytest_extra_args = []
    # Install deps and the package itself.
    if cohabitation is True or cohabitation is None:
        install_env = {"URLLIB3_NO_OVERRIDE": "1"}

        session.install(
            f".[{extras}]",
            "--no-binary",
            "urllib3-future",
            silent=False,
            env=install_env,
        )
        session.install("-r", "requirements-dev.txt")
    else:
        if override_dev_deps is None:
            session.install("-r", "requirements-dev.txt")
        else:
            session.install("-r", override_dev_deps)

        if extras:
            session.install(
                f".[{extras}]",
                silent=False,
            )
        else:
            session.install(
                ".",
                silent=False,
            )

    # Show the pip version.
    session.run("pip", "--version")
    session.run("python", "--version")

    if cohabitation is True:
        session.run("pip", "install", "urllib3")
        session.run("python", "-m", "niquests.help")
    elif cohabitation is None:
        session.run("python", "-m", "niquests.help")

    with local_http_stack(session, with_revocation=with_revocation) as processes:
        session.run(
            "python",
            "-m",
            "coverage",
            "run",
            "--parallel-mode",
            "-m",
            "pytest",
            "-v",
            "-ra",
            f"--color={'yes' if 'GITHUB_ACTIONS' in os.environ else 'auto'}",
            "--tb=native",
            "--durations=10",
            "--strict-config",
            "--strict-markers",
            *pytest_extra_args,
            *(session.posargs or (("tests/",) if not pytest_extra_args else ())),
            env={
                "PYTHONWARNINGS": "always::DeprecationWarning",
                "TRAEFIK_HTTPBIN_ENABLE": "true" if processes is not None else "false",
                "TRAEFIK_HTTPBIN_IPV4": os.environ.get("TRAEFIK_HTTPBIN_IPV4", "127.0.0.1"),
            },
        )


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15", "pypy3.11"])
def test(session: nox.Session) -> None:
    tests_impl(session)


@nox.session(python="3.13")
def local_server(session: nox.Session) -> None:
    """Serve the local stack until Ctrl-C; --no-revocation starts only Docker in the background."""
    if session.posargs not in ([], ["--no-revocation"]):
        session.error("the only supported option is --no-revocation")
    detached = bool(session.posargs)
    session.install("trustme==1.2.1", "cryptography>=39")
    with local_http_stack(session, stop_on_exit=not detached, with_revocation=not detached) as processes:
        if processes is None:
            session.error("The local protocol stack could not be started")
        if not detached:
            session.log("Local protocol and revocation services are running; press Ctrl-C to stop")
            try:
                while True:
                    for process in processes:
                        if process.poll() is not None:
                            session.error(f"Local revocation service exited: {process.args}")
                    time.sleep(1)
            except KeyboardInterrupt:
                pass


@nox.session(python="3.12")
def revocation(session: nox.Session) -> None:
    """Run opt-in fixture smoke tests and strict OCSP/CRL integration without silent skips."""
    session.env["NIQUESTS_REQUIRE_REVOCATION"] = "1"
    tests_impl(
        session,
        extras="ocsp",
        pytest_extra_args=["tests/test_revocation_fixtures.py", "tests/test_ocsp.py", "tests/test_crl.py"],
    )


@nox.session(
    python=[
        "3.11",
    ]
)
def test_cohabitation(session: nox.Session) -> None:
    tests_impl(session, cohabitation=True)
    tests_impl(session, cohabitation=None)


@nox.session
def lint(session: nox.Session) -> None:
    session.install("pre-commit")
    session.run("pre-commit", "run", "--all-files")


@nox.session
def docs(session: nox.Session) -> None:
    session.install("-r", "docs/requirements.txt")
    session.install(".[socks]")

    session.chdir("docs")
    if os.path.exists("_build"):
        shutil.rmtree("_build")
    session.run("sphinx-build", "-b", "html", ".", "_build/html")


@nox.session
def i18n(session: nox.Session) -> None:
    session.install("-r", "docs/requirements.txt")
    session.install(".[socks]")

    session.chdir("docs")

    if os.path.exists("_build"):
        shutil.rmtree("_build")

    session.run("sphinx-build", "-b", "gettext", ".", "_build/gettext")
    session.run("sphinx-intl", "update", "-p", "_build/gettext", "-l", "fr_FR")


@nox.session(python="3.12")
def pyodideconsole(session: nox.Session) -> None:
    # build wheel into dist folder
    # Run build and capture output
    session.install("build")
    build_output = session.run("python", "-m", "build", "--wheel", silent=True)
    assert build_output

    session.run("python", "-m", "http.server", "-d", "dist", "-b", "localhost")


@nox.session(python="3.13")
@nox.parametrize("runner", ["node", "firefox", "chrome"], ids=["node", "firefox", "chrome"])
def emscripten(session: nox.Session, runner: str) -> None:
    """Test on Emscripten with Pyodide & Chrome / Firefox / Node.js"""
    if runner == "node":
        print(
            "Node version:",
            session.run("node", "--version", silent=True, external=True),
        )

    session.install("build", "trustme==1.2.1")

    # make sure we have a dist dir for pyodide
    pyodide_version = "0.28.1"

    pyodide_artifacts_path = Path(session.cache_dir) / f"pyodide-{pyodide_version}"

    if not pyodide_artifacts_path.exists():
        print("Fetching pyodide build artifacts")
        session.run(
            "curl",
            "-L",
            f"https://github.com/pyodide/pyodide/releases/download/{pyodide_version}/pyodide-{pyodide_version}.tar.bz2",
            "--output-dir",
            session.cache_dir,
            "-O",
            external=True,
        )
        pyodide_artifacts_path.mkdir(parents=True)
        session.run(
            "tar",
            "-xjf",
            f"{pyodide_artifacts_path}.tar.bz2",
            "-C",
            str(pyodide_artifacts_path),
            "--strip-components",
            "1",
            external=True,
        )

    dist_dir = pyodide_artifacts_path

    if os.path.exists("dist"):
        shutil.rmtree("dist")

    session.run("python", "-m", "build")

    # Copy the wheel into the pyodide dist dir with a fixed name so test code
    # can reference it without knowing the version. The name must be a valid
    # PEP 427 wheel filename for Pyodide's wheel parser.
    wheel_file = next(Path("dist").glob("*.whl"))
    fixed_wheel_name = "niquests-0.0.dev0-py3-none-any.whl"
    shutil.copy(wheel_file, dist_dir / fixed_wheel_name)

    assert dist_dir is not None
    assert dist_dir.exists()

    tests_impl(
        session,
        extras="",
        pytest_extra_args=[
            "--runtime",
            f"{runner}-no-host",
            "--dist-dir",
            str(dist_dir),
            "tests/test_emscripten.py",
            "-v",
        ],
        override_dev_deps="requirements-wasm.txt",
        with_revocation=False,
    )


@nox.session(python="3.13")
def wasi(session: nox.Session) -> None:
    """Build and execute the WASI HTTP 0.2/0.3 component tests under Wasmtime."""
    session.install("-r", "requirements-wasi.txt")
    session.install(".")

    componentize_version = "0.25.0"
    componentize_source_override = os.environ.get("COMPONENTIZE_SOURCE")
    componentize_source = (
        Path(componentize_source_override)
        if componentize_source_override
        else Path(session.cache_dir) / f"componentize-py-{componentize_version}-source"
    )
    if not componentize_source.exists():
        metadata_url = f"https://pypi.org/pypi/componentize-py/{componentize_version}/json"
        with urllib.request.urlopen(metadata_url) as response:
            metadata = json.load(response)
        source_url = next(item["url"] for item in metadata["urls"] if item["packagetype"] == "sdist")
        archive = Path(session.cache_dir) / f"componentize-py-{componentize_version}.tar.gz"
        urllib.request.urlretrieve(source_url, archive)
        extract_root = Path(session.cache_dir) / f"componentize-py-{componentize_version}-extract"
        extract_root.mkdir(exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(extract_root, filter="data")
        extracted = next(path for path in extract_root.iterdir() if (path / "wit").is_dir())
        shutil.move(extracted, componentize_source)

    wasmtime = os.environ.get("WASMTIME") or shutil.which("wasmtime") or str(Path.home() / ".wasmtime" / "bin" / "wasmtime")
    if not Path(wasmtime).is_file():
        session.error(f"Wasmtime was not found at {wasmtime!r}; set WASMTIME to its executable path")

    site_packages = session.run(
        "python",
        "-c",
        "import site; print(site.getsitepackages()[0])",
        silent=True,
    )
    assert site_packages
    root = Path.cwd().resolve()
    guest = root / "tests" / "wasi_guest"
    artifacts = Path(session.cache_dir) / "wasi-dist"
    if artifacts.exists():
        shutil.rmtree(artifacts)
    artifacts.mkdir()
    wasi_coverage = root / ".coverage.wasi"
    if wasi_coverage.exists():
        wasi_coverage.unlink()
    old_site_packages = Path(session.cache_dir) / "wasi-urllib3-2.23.900"
    if old_site_packages.exists():
        shutil.rmtree(old_site_packages)
    session.run(
        "python",
        "-m",
        "pip",
        "install",
        "--target",
        str(old_site_packages),
        "urllib3.future==2.23.900",
    )
    no_tls_site_packages = Path(session.cache_dir) / "wasi-no-tls"
    if no_tls_site_packages.exists():
        shutil.rmtree(no_tls_site_packages)
    session.run(
        "python",
        "-m",
        "pip",
        "install",
        "--target",
        str(no_tls_site_packages),
        "urllib3.future==2.24.900",
        "charset-normalizer",
        "wassima",
        "pytest>=9,<10",
        "coverage==7.15.2",
        "packaging",
    )

    sync_component = artifacts / "niquests-sync-p2.wasm"
    async_component = artifacts / "niquests-async-p3.wasm"
    socket_sync_component = artifacts / "niquests-socket-sync-p2.wasm"
    socket_async_component = artifacts / "niquests-socket-async-p3.wasm"
    unavailable_sync_component = artifacts / "niquests-unavailable-sync-p2.wasm"
    unavailable_async_component = artifacts / "niquests-unavailable-async-p3.wasm"
    hybrid_sync_component = artifacts / "niquests-hybrid-sync-p2.wasm"
    hybrid_async_component = artifacts / "niquests-hybrid-async-p3.wasm"
    p1_sync_component = artifacts / "niquests-p1-sync.wasm"
    combined_component = artifacts / "niquests-combined-p3.wasm"
    common_componentize_args = [
        "componentize",
        "app",
        "-p",
        str(root / "src"),
        "-p",
        str(guest),
        "-p",
        site_packages.strip(),
    ]

    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-d",
        str(guest / "wit"),
        "-w",
        "niquests:test/sync-http-command",
        *common_componentize_args,
        "-p",
        str(guest / "sync"),
        "-o",
        str(sync_component),
    )
    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-d",
        str(guest / "wit"),
        "-w",
        "niquests:test/async-http-command",
        *common_componentize_args,
        "-p",
        str(guest / "async"),
        "-o",
        str(async_component),
    )
    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-w",
        "wasi:cli/command@0.2.0",
        *common_componentize_args,
        "-p",
        str(guest / "socket_sync"),
        "-o",
        str(socket_sync_component),
    )
    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-w",
        "wasi:cli/command@0.3.0",
        *common_componentize_args,
        "-p",
        str(guest / "socket_async"),
        "-o",
        str(socket_async_component),
    )
    for world, profile, output in (
        ("niquests:test/sync-empty-command", "unavailable_sync", unavailable_sync_component),
        ("niquests:test/async-empty-command", "unavailable_async", unavailable_async_component),
    ):
        session.run(
            "componentize-py",
            "-d",
            str(componentize_source / "wit"),
            "-d",
            str(guest / "wit"),
            "-w",
            world,
            "componentize",
            "app",
            "-p",
            str(root / "src"),
            "-p",
            str(guest),
            "-p",
            str(old_site_packages),
            "-p",
            site_packages.strip(),
            "-p",
            str(guest / profile),
            "-o",
            str(output),
            env={"VIRTUAL_ENV": ""},
        )
    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-d",
        str(guest / "wit"),
        "-w",
        "niquests:test/sync-empty-command",
        "componentize",
        "app",
        "-p",
        str(root / "src"),
        "-p",
        str(guest),
        "-p",
        str(no_tls_site_packages),
        "-p",
        str(guest / "p1_sync"),
        "-o",
        str(p1_sync_component),
        env={"VIRTUAL_ENV": ""},
    )
    session.run(
        "componentize-py",
        "-d",
        str(componentize_source / "wit"),
        "-d",
        str(guest / "wit"),
        "-w",
        "niquests:test/combined-command",
        *common_componentize_args,
        "-p",
        str(guest / "combined"),
        "-o",
        str(combined_component),
    )
    for world, profile, output in (
        ("niquests:test/sync-hybrid-command", "hybrid_sync", hybrid_sync_component),
        ("niquests:test/async-hybrid-command", "hybrid_async", hybrid_async_component),
    ):
        session.run(
            "componentize-py",
            "-d",
            str(componentize_source / "wit"),
            "-d",
            str(guest / "wit"),
            "-w",
            world,
            "componentize",
            "app",
            "-p",
            str(root / "src"),
            "-p",
            str(guest),
            "-p",
            str(no_tls_site_packages),
            "-p",
            str(guest / profile),
            "-o",
            str(output),
            env={"VIRTUAL_ENV": ""},
        )

    preopens = [
        "--dir",
        f"{root}::/workspace",
        "--dir",
        "/dev",
        "--dir",
        f"{artifacts}::/artifacts",
    ]
    try:
        with socket.create_connection(("httpbingo.org", 443), timeout=1):
            wan_available = True
    except OSError:
        wan_available = False
    session.run(
        wasmtime,
        "run",
        "-S",
        "http",
        "--env",
        f"NIQUESTS_WASI_WAN_AVAILABLE={str(wan_available).lower()}",
        *preopens,
        str(sync_component),
        external=True,
    )
    session.run(
        wasmtime,
        "run",
        "-Sinherit-network",
        "-Sallow-ip-name-lookup=y",
        *preopens,
        str(socket_sync_component),
        external=True,
    )
    session.run(
        wasmtime,
        "run",
        "-Sinherit-network",
        "-Sallow-ip-name-lookup=y",
        *preopens,
        str(p1_sync_component),
        external=True,
    )
    session.run(wasmtime, "run", *preopens, str(unavailable_sync_component), external=True)
    session.run(
        wasmtime,
        "run",
        "-Shttp",
        "-Sinherit-network",
        "-Sallow-ip-name-lookup=y",
        *preopens,
        str(hybrid_sync_component),
        external=True,
    )
    session.run(
        "python",
        "-m",
        "pytest",
        "-v",
        "-s",
        "tests/test_wasi_async_components.py",
        env={
            "NIQUESTS_WASI_ARTIFACTS": str(artifacts),
            "NIQUESTS_WASMTIME": wasmtime,
            "NIQUESTS_WASI_ROOT": str(root),
        },
    )

    coverage_env = {"COVERAGE_FILE": str(wasi_coverage)}
    session.run(
        "coverage",
        "combine",
        str(artifacts),
        env=coverage_env,
    )
    session.run(
        "coverage",
        "report",
        "--show-missing",
        "--skip-covered",
        "--include=src/niquests/extensions/wasi/*",
        "--fail-under=100",
        env=coverage_env,
    )

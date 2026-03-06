from __future__ import annotations

import os
import shutil
from pathlib import Path

import nox


def tests_impl(
    session: nox.Session,
    extras: str = "socks,ws",
    cohabitation: bool | None = False,
    pytest_extra_args: list[str] | None = None,
    override_dev_deps: str | None = None,
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
            "NIQUESTS_STRICT_OCSP": "1",
        },
    )


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "pypy"])
def test(session: nox.Session) -> None:
    tests_impl(session)


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

    session.install("build")

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
    )

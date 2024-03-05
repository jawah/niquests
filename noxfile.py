from __future__ import annotations

import os
import shutil

import nox


def tests_impl(
    session: nox.Session,
    extras: str = "socks",
    cohabitation: bool = False,
) -> None:
    # Install deps and the package itself.
    session.install("-r", "requirements-dev.txt")
    session.install(f".[{extras}]", silent=False)

    # Show the pip version.
    session.run("pip", "--version")
    session.run("python", "--version")

    if cohabitation:
        session.run("pip", "install", "urllib3")
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
        *(session.posargs or ("tests/",)),
        env={"PYTHONWARNINGS": "always::DeprecationWarning"},
    )


@nox.session(python=["3.7", "3.8", "3.9", "3.10", "3.11", "3.12", "pypy"])
def test(session: nox.Session) -> None:
    tests_impl(session)


@nox.session(
    python=[
        "3.11",
    ]
)
def test_cohabitation(session: nox.Session) -> None:
    tests_impl(session, cohabitation=True)


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

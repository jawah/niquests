from __future__ import annotations

from unittest import mock

from niquests.help import info


def test_system_ssl():
    """Verify we're actually setting system_ssl when it should be available."""
    assert info()["system_ssl"]["version"] != ""


class VersionedPackage:
    def __init__(self, version):
        self.__version__ = version


def test_idna_without_version_attribute():
    """Older versions of IDNA don't provide a __version__ attribute, verify
    that if we have such a package, we don't blow up.
    """
    with mock.patch("niquests.help.idna", new=None):
        assert info()["idna"] == {"version": ""}


def test_idna_with_version_attribute():
    """Verify we're actually setting idna version when it should be available."""
    with mock.patch("niquests.help.idna", new=VersionedPackage("2.6")):
        assert info()["idna"] == {"version": "2.6"}

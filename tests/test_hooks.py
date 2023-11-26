from __future__ import annotations

import pytest

from niquests import hooks


def hook(value):
    return value[1:]


@pytest.mark.parametrize(
    "hooks_list, result",
    (
        (hook, "ata"),
        ([hook, lambda x: None, hook], "ta"),
    ),
)
def test_hooks(hooks_list, result):
    assert hooks.dispatch_hook("response", {"response": hooks_list}, "Data") == result


@pytest.mark.parametrize(
    "hooks_list, result",
    (
        (hook, "ata"),
        ([hook, lambda x: None, hook], "ta"),
    ),
)
def test_hooks_with_kwargs(hooks_list, result):
    assert (
        hooks.dispatch_hook(
            "response", {"response": hooks_list}, "Data", should_not_crash=True
        )
        == result
    )


def test_default_hooks():
    assert hooks.default_hooks() == {
        "pre_request": [],
        "pre_send": [],
        "on_upload": [],
        "response": [],
    }

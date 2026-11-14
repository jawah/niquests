from __future__ import annotations

import sys

import pytest

from niquests import hooks


def hook(value):
    return value[1:]


async def ahook(value):
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
    assert hooks.dispatch_hook("response", {"response": hooks_list}, "Data", should_not_crash=True) == result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hooks_list, result",
    (
        (ahook, "ata"),
        ([ahook, lambda x: None, hook], "ta"),
    ),
)
async def test_ahooks(hooks_list, result):
    assert (await hooks.async_dispatch_hook("response", {"response": hooks_list}, "Data")) == result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hooks_list, result",
    (
        (hook, "ata"),
        ([hook, lambda x: None, ahook], "ta"),
    ),
)
async def test_ahooks_with_kwargs(hooks_list, result):
    assert (await hooks.async_dispatch_hook("response", {"response": hooks_list}, "Data", should_not_crash=True)) == result


def test_default_hooks():
    assert hooks.default_hooks() == {
        "pre_request": [],
        "pre_send": [],
        "on_upload": [],
        "early_response": [],
        "response": [],
    }


@pytest.mark.parametrize("alias", ("HookType", "AsyncHookType"))
@pytest.mark.parametrize("parameterized", (False, True))
def test_public_hook_alias_can_resolve_type_hints(alias, parameterized):
    import typing

    namespace = {}
    annotation = f"{alias}[int]" if parameterized else alias
    exec(
        f"from niquests.typing import {alias}\nclass Client:\n    hooks: {annotation}\n",
        namespace,
    )
    hints = typing.get_type_hints(namespace["Client"], globalns=namespace)
    lifecycle = hooks.AsyncLifeCycleHook if alias == "AsyncHookType" else hooks.LifeCycleHook
    assert (lifecycle[int] if parameterized else lifecycle[hooks._HV]) in hints["hooks"].__args__


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Session annotations use PEP 604 unions")
@pytest.mark.parametrize("session", ("Session", "AsyncSession"))
def test_session_hook_parameter_can_resolve_type_hints(session):
    import typing

    import niquests

    assert typing.get_type_hints(getattr(niquests, session).__init__)["hooks"]

from __future__ import annotations

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


def test_hook_type_aliases_are_eagerly_resolvable():
    # the unions must hold the real hook classes, not forward references,
    # so that typing.get_type_hints works in any downstream module namespace
    # (see https://github.com/jawah/niquests/issues/487)
    import typing

    import niquests.typing
    from niquests.hooks import AsyncHookType, AsyncLifeCycleHook, HookType, LifeCycleHook

    for alias, klass in ((HookType, LifeCycleHook), (AsyncHookType, AsyncLifeCycleHook)):
        assert not any(
            isinstance(arg, typing.ForwardRef) for arg in typing.get_args(alias)
        ), "alias still holds a forward reference"
        assert any(
            getattr(arg, "__origin__", arg) is klass for arg in typing.get_args(alias)
        ), "alias does not reference the hook class"

    assert typing.get_type_hints(hooks.dispatch_hook)
    assert typing.get_type_hints(hooks.async_dispatch_hook)


def test_hook_type_aliases_lazy_reexport():
    import niquests.typing
    from niquests.hooks import AsyncHookType, HookType

    assert niquests.typing.HookType is HookType
    assert niquests.typing.AsyncHookType is AsyncHookType

    with pytest.raises(AttributeError):
        niquests.typing.NoSuchTypeAlias


def test_session_constructor_type_hints_resolve():
    # the exact downstream failure from issue 487: resolving the annotations
    # of the session constructors in their own module namespace
    import typing

    from niquests.async_session import AsyncSession
    from niquests.sessions import Session

    assert "hooks" in typing.get_type_hints(Session.__init__)
    assert "hooks" in typing.get_type_hints(AsyncSession.__init__)

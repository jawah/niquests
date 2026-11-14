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


@pytest.mark.parametrize("left_type", (hooks.LifeCycleHook, hooks.AsyncLifeCycleHook))
@pytest.mark.parametrize("right_type", (hooks.LifeCycleHook, hooks.AsyncLifeCycleHook))
def test_combining_hooks_does_not_mutate_or_share_operand_lists(left_type, right_type):
    left, right = left_type(), right_type()
    left_before = {event: list(values) for event, values in left.items()}
    right_before = {event: list(values) for event, values in right.items()}

    combined = left + right

    assert dict(left.items()) == left_before
    assert dict(right.items()) == right_before
    for event in hooks.HOOKS:
        assert combined[event] == left_before[event] + right_before[event]
        assert combined[event] is not left[event]
        assert combined[event] is not right[event]
        combined[event].append(hook)
        assert left[event] == left_before[event]
        assert right[event] == right_before[event]
        left[event].append(hook)
        right[event].append(hook)
        assert combined[event] == left_before[event] + right_before[event] + [hook]


def test_reusing_a_hook_in_another_chain_does_not_accumulate_callbacks():
    seen = []

    class Recorder(hooks.LifeCycleHook):
        def __init__(self, name):
            super().__init__()
            self.name = name

        def response(self, value):
            seen.append(self.name)
            return value

    left, first, second = Recorder("left"), Recorder("first"), Recorder("second")
    first_chain = left + first
    second_chain = left + second
    hooks.dispatch_hook("response", first_chain, "data")
    assert seen == ["left", "first"]
    seen.clear()
    hooks.dispatch_hook("response", second_chain, "data")
    assert seen == ["left", "second"]

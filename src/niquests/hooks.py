"""
requests.hooks
~~~~~~~~~~~~~~

This module provides the capabilities for the Requests hooks system.

Available hooks:

``response``:
    The response generated from a Request.
"""
from __future__ import annotations

import typing

from ._typing import _HV, HookCallableType, HookType

HOOKS = ["response"]


def default_hooks() -> HookType:
    return {event: [] for event in HOOKS}


# TODO: response is the only one


def dispatch_hook(
    key: str, hooks: HookType | None, hook_data: _HV, **kwargs: typing.Any
) -> _HV:
    """Dispatches a hook dictionary on a given piece of data."""
    if hooks is None:
        return hook_data

    callables: list[HookCallableType] | HookCallableType | None = hooks.get(key)

    if callables:
        if callable(callables):
            callables = [callables]
        for hook in callables:
            _hook_data = hook(hook_data, **kwargs)
            if _hook_data is not None:
                hook_data = _hook_data

    return hook_data

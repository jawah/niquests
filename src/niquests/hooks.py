"""
requests.hooks
~~~~~~~~~~~~~~

This module provides the capabilities for the Requests hooks system.

Available hooks:

``pre_request``:
    The prepared request just got built. You may alter it prior to be sent through HTTP.
``pre_send``:
    The prepared request got his ConnectionInfo injected. This event is triggered just after picking a live connection from the pool.
``response``:
    The response generated from a Request.
"""
from __future__ import annotations

import typing

from ._typing import _HV, HookCallableType, HookType

HOOKS = [
    "pre_request",
    "pre_send",
    "response",
]


def default_hooks() -> HookType[_HV]:
    return {event: [] for event in HOOKS}


def dispatch_hook(
    key: str, hooks: HookType[_HV] | None, hook_data: _HV, **kwargs: typing.Any
) -> _HV:
    """Dispatches a hook dictionary on a given piece of data."""
    if hooks is None:
        return hook_data

    callables: list[HookCallableType[_HV]] | HookCallableType[_HV] | None = hooks.get(
        key
    )

    if callables:
        if callable(callables):
            callables = [callables]
        for hook in callables:
            try:
                _hook_data = hook(hook_data, **kwargs)
            except TypeError:
                _hook_data = hook(hook_data)
            if _hook_data is not None:
                hook_data = _hook_data

    return hook_data

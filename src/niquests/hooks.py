"""
requests.hooks
~~~~~~~~~~~~~~

This module provides the capabilities for the Requests hooks system.

Available hooks:

``pre_request``:
    The prepared request just got built. You may alter it prior to be sent through HTTP.
``pre_send``:
    The prepared request got his ConnectionInfo injected.
    This event is triggered just after picking a live connection from the pool.
``on_upload``:
    Permit to monitor the upload progress of passed body.
    This event is triggered each time a block of data is transmitted to the remote peer.
    Use this hook carefully as it may impact the overall performance.
``response``:
    The response generated from a Request.
"""

from __future__ import annotations

import asyncio
import typing
from collections.abc import MutableMapping

from ._typing import (
    _HV,
    AsyncHookCallableType,
    AsyncHookType,
    HookCallableType,
    HookType,
)

if typing.TYPE_CHECKING:
    from .models import PreparedRequest, Response

HOOKS = [
    "pre_request",
    "pre_send",
    "on_upload",
    "early_response",
    "response",
]


def default_hooks() -> HookType[_HV]:
    return {event: [] for event in HOOKS}


def dispatch_hook(key: str, hooks: HookType[_HV] | None, hook_data: _HV, **kwargs: typing.Any) -> _HV:
    """Dispatches a hook dictionary on a given piece of data."""
    if hooks is None:
        return hook_data

    callables: list[HookCallableType[_HV]] | None = hooks.get(key)  # type: ignore[assignment]

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


async def async_dispatch_hook(key: str, hooks: AsyncHookType[_HV] | None, hook_data: _HV, **kwargs: typing.Any) -> _HV:
    """Dispatches a hook dictionary on a given piece of data asynchronously."""
    if hooks is None:
        return hook_data

    callables: list[HookCallableType[_HV] | AsyncHookCallableType[_HV]] | None = hooks.get(key)

    if callables:
        if callable(callables):
            callables = [callables]
        for hook in callables:
            if asyncio.iscoroutinefunction(hook):
                try:
                    _hook_data = await hook(hook_data, **kwargs)
                except TypeError:
                    _hook_data = await hook(hook_data)
            else:
                try:
                    _hook_data = hook(hook_data, **kwargs)
                except TypeError:
                    _hook_data = hook(hook_data)

            if _hook_data is not None:
                hook_data = _hook_data

    return hook_data


class _BaseLifeCycleHook(
    typing.MutableMapping[str, typing.List[typing.Union[HookCallableType, AsyncHookCallableType]]], typing.Generic[_HV]
):
    def __init__(self) -> None:
        self._store: MutableMapping[str, list[HookCallableType[_HV] | AsyncHookCallableType[_HV]]] = {
            "pre_request": [],
            "pre_send": [],
            "on_upload": [],
            "early_response": [],
            "response": [],
        }

    def __setitem__(self, key: str | bytes, value: list[HookCallableType[_HV] | AsyncHookCallableType[_HV]]) -> None:
        raise NotImplementedError("LifeCycleHook is Read Only")

    def __getitem__(self, key: str) -> list[HookCallableType[_HV] | AsyncHookCallableType[_HV]]:
        return self._store[key]

    def get(self, key: str) -> list[HookCallableType[_HV] | AsyncHookCallableType[_HV]]:  # type: ignore[override]
        return self[key]

    def __add__(self, other) -> _BaseLifeCycleHook:
        if not isinstance(other, _BaseLifeCycleHook):
            raise TypeError

        tmp_store = {}
        combined_hooks: _BaseLifeCycleHook[_HV] = _BaseLifeCycleHook()

        for h, fns in self._store.items():
            tmp_store[h] = fns
            tmp_store[h] += other._store[h]

        combined_hooks._store = tmp_store

        return combined_hooks

    def __iter__(self):
        yield from self._store

    def items(self):
        for key in self:
            yield key, self[key]

    def __delitem__(self, key):
        raise NotImplementedError("LifeCycleHook is Read Only")

    def __len__(self):
        return len(self._store)


class LifeCycleHook(_BaseLifeCycleHook[_HV]):
    """
    A sync-only middleware to be used in your request/response lifecycles.
    """

    def __init__(self) -> None:
        super().__init__()
        self._store.update(
            {
                "pre_request": [self.pre_request],  # type: ignore[list-item]
                "pre_send": [self.pre_send],  # type: ignore[list-item]
                "on_upload": [self.on_upload],  # type: ignore[list-item]
                "early_response": [self.early_response],  # type: ignore[list-item]
                "response": [self.response],  # type: ignore[list-item]
            }
        )

    def pre_request(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> PreparedRequest | None:
        """The prepared request just got built. You may alter it prior to be sent through HTTP."""
        return None

    def pre_send(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> None:
        """The prepared request got his ConnectionInfo injected. This event is triggered just
        after picking a live connection from the pool. You may not alter the prepared request."""
        return None

    def on_upload(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> None:
        """Permit to monitor the upload progress of passed body. This event is triggered each time
        a block of data is transmitted to the remote peer. Use this hook carefully as
        it may impact the overall performance. You may not alter the prepared request."""
        return None

    def early_response(self, response: Response, **kwargs: typing.Any) -> None:
        """An early response caught before receiving the final Response for a given Request.
        Like but not limited to 103 Early Hints."""
        return None

    def response(self, response: Response, **kwargs: typing.Any) -> Response | None:
        """The response generated from a Request. You may alter the response at will."""
        return None


class AsyncLifeCycleHook(_BaseLifeCycleHook[_HV]):
    """
    An async-only middleware to be used in your request/response lifecycles.
    """

    def __init__(self) -> None:
        super().__init__()
        self._store.update(
            {
                "pre_request": [self.pre_request],  # type: ignore[list-item]
                "pre_send": [self.pre_send],  # type: ignore[list-item]
                "on_upload": [self.on_upload],  # type: ignore[list-item]
                "early_response": [self.early_response],  # type: ignore[list-item]
                "response": [self.response],  # type: ignore[list-item]
            }
        )

    async def pre_request(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> PreparedRequest | None:
        """The prepared request just got built. You may alter it prior to be sent through HTTP."""
        return None

    async def pre_send(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> None:
        """The prepared request got his ConnectionInfo injected. This event is triggered just
        after picking a live connection from the pool. You may not alter the prepared request."""
        return None

    async def on_upload(self, prepared_request: PreparedRequest, **kwargs: typing.Any) -> None:
        """Permit to monitor the upload progress of passed body. This event is triggered each time
        a block of data is transmitted to the remote peer. Use this hook carefully as
        it may impact the overall performance. You may not alter the prepared request."""
        return None

    async def early_response(self, response: Response, **kwargs: typing.Any) -> None:
        """An early response caught before receiving the final Response for a given Request.
        Like but not limited to 103 Early Hints."""
        return None

    async def response(self, response: Response, **kwargs: typing.Any) -> Response | None:
        """The response generated from a Request. You may alter the response at will."""
        return None

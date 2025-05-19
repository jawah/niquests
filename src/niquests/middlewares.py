"""
Middlewares implement a way of intercepting requests at different points in the request lifecycle. They allow modifying the request and/or response, and/or trigger events.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import PreparedRequest, Response


class Middleware(ABC):
    """Base class for synchronous middlewares."""

    def pre_request(self, request: PreparedRequest) -> None:
        """Called before the request is sent."""

    def pre_send(self, request: PreparedRequest) -> None:
        """The prepared request got his ConnectionInfo injected.
        This event is triggered just after picking a live connection from the pool"""

    def on_upload(
        self, request: PreparedRequest
    ) -> None:  # consider passing the block of data in question as a parameter. (requires changes in urllib3.future)
        """Permit to monitor the upload progress of passed body.
        This event is triggered each time a block of data is transmitted to the remote peer.
        Use this hook carefully as it may impact the overall performance."""

    def early_response(self, response: Response) -> None:
        """An early response caught before receiving the final Response for a given Request. Like but not limited to 103 Early Hints.
        This event is triggered before the Response is returned to the user."""

    def response(self, response: Response) -> None:
        """Called when a response is received."""


class AsyncMiddleware(ABC):
    """Base class for asynchronous middlewares."""

    async def pre_request(self, request: PreparedRequest) -> None:
        """Called before the request is sent."""

    async def pre_send(self, request: PreparedRequest) -> None:
        """The prepared request got his ConnectionInfo injected.
        This event is triggered just after picking a live connection from the pool"""

    async def on_upload(self, request: PreparedRequest) -> None:
        """Permit to monitor the upload progress of passed body.
        This event is triggered each time a block of data is transmitted to the remote peer.
        Use this hook carefully as it may impact the overall performance."""

    async def early_response(self, response: Response) -> None:
        """An early response caught before receiving the final Response for a given Request. Like but not limited to 103 Early Hints.
        This event is triggered before the Response is returned to the user."""

    async def response(self, response: Response) -> None:
        """Called when a response is received."""



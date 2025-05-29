"""
Middlewares implement a way of intercepting requests at different points in the request lifecycle.
They allow modifying the request and/or response, and/or trigger events.
"""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import PreparedRequest, Response
    from .sessions import Session


class Middleware(ABC):
    """Base class for synchronous middlewares."""

    def pre_request(self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any) -> None:
        """Called before the request is sent."""

    def pre_send(self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any) -> None:
        """The prepared request got his ConnectionInfo injected.
        This event is triggered just after picking a live connection from the pool"""

    def on_upload(
        self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any
    ) -> None:  # consider passing the block of data in question as a parameter. (requires changes in urllib3.future)
        """Permit to monitor the upload progress of passed body.
        This event is triggered each time a block of data is transmitted to the remote peer.
        Use this hook carefully as it may impact the overall performance."""

    def early_response(self, session: Session, response: Response, *args: Any, **kwargs: Any) -> None:
        """An early response caught before receiving the final Response for a given Request.
        Like but not limited to 103 Early Hints.
        This event is triggered before the Response is returned to the user."""

    def response(self, session: Session, response: Response, *args: Any, **kwargs: Any) -> None:
        """Called when a response is received."""

    def on_exception(self, session: Session, request: PreparedRequest, exception: Exception, *args: Any, **kwargs: Any) -> bool:
        """Return True to confirm the exception was successfully handled, preventing it from propagating further.
        Note: All registered middlewares for this event will be called regardless of this method’s return value,
        but if any middleware returns True, the exception will be suppressed."""
        return False


class AsyncMiddleware(Middleware):
    """Base class for asynchronous middlewares."""

    async def pre_request(self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Called before the request is sent."""

    async def pre_send(self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """The prepared request got his ConnectionInfo injected.
        This event is triggered just after picking a live connection from the pool"""

    async def on_upload(self, session: Session, request: PreparedRequest, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Permit to monitor the upload progress of passed body.
        This event is triggered each time a block of data is transmitted to the remote peer.
        Use this hook carefully as it may impact the overall performance."""

    async def early_response(self, session: Session, response: Response, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """An early response caught before receiving the final Response for a given Request.
         Like but not limited to 103 Early Hints.
        This event is triggered before the Response is returned to the user."""

    async def response(self, session: Session, response: Response, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        """Called when a response is received."""

    async def on_exception(self, session: Session, request: PreparedRequest, exception: Exception, *args: Any, **kwargs: Any) -> bool:  # type: ignore[override]
        """Return True to confirm the exception was successfully handled, preventing it from propagating further.
        Note: All registered middlewares for this event will be called regardless of this method’s return value,
        but if any middleware returns True, the exception will be suppressed."""
        return False
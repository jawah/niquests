import typing
from inspect import iscoroutinefunction
from abc import ABC

if typing.TYPE_CHECKING:
    from .models import PreparedRequest, Response


class Middleware(ABC):
    """Base class for synchronous request lifecycle middlewares."""

    def on_request(self, request: 'PreparedRequest', *args, **kwargs) -> None:
        """Called after the request is prepared but before it’s sent.

        :param request: The prepared request object.
        :param kwargs: Additional context.
        """
        pass

    def on_response(self, response: 'Response', *args, **kwargs) -> None:
        """Called after receiving a response.

        :param response: The response object.
        :param kwargs: Additional context.
        """
        pass


class MiddlewareExecutor:
    """Executes a chain of middleware for different stages of a request lifecycle."""

    def __init__(self, middlewares: list[Middleware] = None):
        """Initialize with a list of middleware instances."""
        self.middlewares = middlewares or []

    def execute_stage(
            self,
            stage: str,
            *args,
            **kwargs
    ) -> None:
        """
        Execute middleware for a specific stage (e.g., on_request, on_response).

        Args:
            stage: The middleware method to call (e.g., 'on_request', 'on_response').
            *args, **kwargs: Arguments to pass to the middleware method.
        """
        for middleware in self.middlewares:
            getattr(middleware, stage)(*args, **kwargs)

    def on_request(self, request: PreparedRequest, *args, **kwargs) -> None:
        """Execute on_request middleware stage."""
        self.execute_stage("on_request", request=request, *args, **kwargs)

    def on_response(self, response: Response, *args, **kwargs) -> None:
        """Execute on_response middleware stage."""
        self.execute_stage("on_response", response=response, *args, **kwargs)

    def __call__(self, stage: str, *args, **kwargs) -> None:
        """Allow direct stage execution for flexibility."""
        self.execute_stage(stage, *args, **kwargs)


class AsyncMiddlewareExecutor(MiddlewareExecutor):
    """Executes a chain of asynchronous middleware for different stages of a request lifecycle."""

    async def execute_stage(
            self,
            stage: str,
            *args,
            **kwargs
    ) -> None:
        """
        Execute middleware for a specific stage (e.g., on_request, on_response) asynchronously.

        Args:
            stage: The middleware method to call (e.g., 'on_request', 'on_response').
            *args, **kwargs: Arguments to pass to the middleware method.
        """
        for middleware in self.middlewares:
            method = getattr(middleware, stage)
            if iscoroutinefunction(method):
                await method(*args, **kwargs)
            else:
                method(*args, **kwargs)

    async def on_request(self, request: PreparedRequest, *args, **kwargs) -> None:
        """Execute on_request middleware stage asynchronously."""
        await self.execute_stage("on_request", default=request, request=request, *args, **kwargs)

    async def on_response(self, response: Response, *args, **kwargs) -> None:
        """Execute on_response middleware stage asynchronously."""
        await self.execute_stage("on_response", default=response, response=response, *args, **kwargs)

    async def __call__(self, stage: str, *args, **kwargs) -> None:
        """Allow direct stage execution for flexibility."""
        await self.execute_stage(stage, *args, **kwargs)

import typing
from inspect import iscoroutinefunction
from typing import Iterable
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
    """
    MiddlewareExecutor is a class that manages the execution of middleware
    functions during the request lifecycle.
    It allows for the chaining of multiple middleware functions, ensuring
    that each middleware can modify the request or response as needed.
    """

    def __init__(self, middlewares: Iterable[Middleware]):
        self.middlewares = middlewares

    def execute_on_request_sync(self, request: 'PreparedRequest', *args, **kwargs) -> None:
        for middleware in self.middlewares:
            middleware.on_request(request, *args, **kwargs) or request

    def execute_on_response_sync(self, response: 'Response', *args, **kwargs) -> None:
        for middleware in self.middlewares:
            middleware.on_response(response, *args, **kwargs) or response

    async def execute_on_request_async(self, request: 'PreparedRequest', *args, **kwargs) -> None:
        for middleware in self.middlewares:
            if iscoroutinefunction(middleware.on_request):
                await middleware.on_request(request=request, *args, **kwargs)
            else:
                middleware.on_request(request=request, *args, **kwargs)

    async def execute_on_response_async(self, response: 'Response', *args, **kwargs) -> None:
        for middleware in self.middlewares:
            if iscoroutinefunction(middleware.on_response):
                await middleware.on_response(response=response, *args, **kwargs)
            else:
                middleware.on_response(response=response, *args, **kwargs)
from typing import Protocol, TypeVar, Any

T = TypeVar("T")


class ModelAdapter(Protocol):
    def from_data(self, data: Any, model_type: type[T]) -> T:
        pass

    def to_data(self, model: Any) -> bytes:
        pass
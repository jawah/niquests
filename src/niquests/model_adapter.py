from typing import Protocol, TypeVar, Any, Tuple

T = TypeVar("T")


class ModelAdapter(Protocol):
    def from_data(self, data: Any, model_type: type[T]) -> T:
        pass

    def to_data(self, model: Any) -> Tuple[bytes, str]:
        """
        Converts a model to bytes and a content type.
        :param model: The model to convert.
        :return: A tuple of bytes and content type.
        """
        pass
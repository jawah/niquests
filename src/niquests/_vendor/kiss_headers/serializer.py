from __future__ import annotations

from .models import Header, Headers


def encode(headers: Headers) -> dict[str, list[dict]]:
    """
    Provide an opinionated but reliable way to encode headers to dict for serialization purposes.
    """
    result: dict[str, list[dict]] = dict()

    for header in headers:
        if header.name not in result:
            result[header.name] = list()

        encoded_header: dict[str, str | None | list[str]] = dict()

        for attribute, value in header:
            if attribute not in encoded_header:
                encoded_header[attribute] = value
                continue

            if isinstance(encoded_header[attribute], list) is False:
                # Here encoded_header[attribute] most certainly is str
                # Had to silent mypy error.
                encoded_header[attribute] = [encoded_header[attribute]]  # type: ignore

            encoded_header[attribute].append(value)  # type: ignore

        result[header.name].append(encoded_header)

    return result


def decode(encoded_headers: dict[str, list[dict]]) -> Headers:
    """
    Decode any previously encoded headers to a Headers object.
    """
    headers: Headers = Headers()

    for header_name, encoded_header_list in encoded_headers.items():
        if not isinstance(encoded_header_list, list):
            raise ValueError("Decode require first level values to be List")

        for encoded_header in encoded_header_list:
            if not isinstance(encoded_header, dict):
                raise ValueError("Decode require each list element to be Dict")

            header = Header(header_name, "")

            for attr, value in encoded_header.items():
                if value is None:
                    header += attr
                    continue
                if isinstance(value, str):
                    header[attr] = value
                    continue

                for sub_value in value:
                    header.insert(-1, **{attr: sub_value})

            headers += header

    return headers

import json
from typing import Any


def decode_payload(job: Any) -> dict[str, Any]:
    for attribute_name in (
        "payload_json",
        "payload",
        "data",
    ):
        if not hasattr(job, attribute_name):
            continue

        value = getattr(job, attribute_name)

        if value is None:
            continue

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return {
                    "raw": value,
                }

            if isinstance(decoded, dict):
                return decoded

            return {
                "value": decoded,
            }

    return {}

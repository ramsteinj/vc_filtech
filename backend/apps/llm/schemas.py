"""Output-schema validation and the dynamic metadata schema (specs/07 §2, specs/06 §5)."""

import json

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from .prompt_defaults import CONFIDENCE, I_NULL, S_NULL, obj

_VALUE_TYPES = {
    "str": S_NULL,
    "date": S_NULL,
    "int": {"type": ["integer", "null"]},
    "float": {"type": ["number", "null"]},
    "bool": {"type": ["boolean", "null"]},
}
JSON_ENCODED_TYPES = {"list", "json", "dimension", "grade"}


def validation_errors(data, schema: dict | None) -> list[str]:
    if not schema:
        return []
    validator = Draft202012Validator(schema)
    return [
        f"{'/'.join(str(p) for p in error.absolute_path) or '(root)'}: {error.message}"
        for error in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))[:10]
    ]


def schema_error(schema) -> str | None:
    if schema is None:
        return None
    if not isinstance(schema, dict):
        return "JSON Schema는 객체여야 합니다."
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        return exc.message
    return None


def metadata_output_schema(fields: list[dict]) -> dict:
    """Strict schema for document.extract_metadata built from a category's field defs.

    list/json/dimension/grade values are requested as JSON strings and decoded later.
    """
    field_schemas = {
        f["key"]: obj(
            {
                "value": _VALUE_TYPES.get(f.get("type", "str"), S_NULL),
                "raw": S_NULL,
                "page": I_NULL,
                "quote": S_NULL,
                "confidence": CONFIDENCE,
            }
        )
        for f in fields
    }
    return obj({"fields": obj(field_schemas), "transcript": S_NULL})


def decode_field_value(field: dict, value):
    """Decode JSON-encoded values for structured field types; keep text if it is not JSON."""
    if value is None or field.get("type") not in JSON_ENCODED_TYPES or not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value

#!/usr/bin/env python3
"""Minimal schema validation for Synrail artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json
except ImportError:
    from synrail_io_v0 import load_json




def validate_node(value, schema: dict, path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: missing required field")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            for key in value:
                if key not in allowed:
                    errors.append(f"{path}.{key}: additional property not allowed")
        for key, child_schema in schema.get("properties", {}).items():
            if key in value:
                validate_node(value[key], child_schema, f"{path}.{key}", errors)
        return

    if expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate_node(item, item_schema, f"{path}[{index}]", errors)
        return

    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string")
            return
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: expected const value {schema['const']}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: expected one of {schema['enum']}")
        return

    if expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer")
            return
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: integer below minimum {schema['minimum']}")
        return

    if expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean")
        return


def validate_document(document: dict, schema: dict) -> list[str]:
    errors: list[str] = []
    validate_node(document, schema, "$", errors)
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-validate-v0")
    parser.add_argument("--schema", required=True)
    parser.add_argument("--document", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    schema = load_json(Path(args.schema))
    document = load_json(Path(args.document))
    errors = validate_document(document, schema)

    if errors:
        print(json.dumps({"result": "INVALID", "errors": errors}, ensure_ascii=True))
        return 2

    print(json.dumps({"result": "VALID"}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

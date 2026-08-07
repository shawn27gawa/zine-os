#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]

ZINE_SCHEMA_PATH = ROOT / "schema" / "zine.schema.json"
BLOCK_SCHEMA_PATH = ROOT / "schema" / "block.schema.json"

DEFAULT_ZINE_PATH = ROOT / "templates" / "basic" / "zine.yaml"

BLOCK_SCHEMA_URI = "https://zineos.dev/schema/block.schema.json"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def display_path(path: Path):
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def validate_zine(zine_path: Path) -> int:
    zine_schema = load_json(ZINE_SCHEMA_PATH)
    block_schema = load_json(BLOCK_SCHEMA_PATH)
    zine_data = load_yaml(zine_path)

    registry = Registry().with_resource(
        BLOCK_SCHEMA_URI,
        Resource.from_contents(block_schema),
    )

    validator = Draft202012Validator(
        zine_schema,
        registry=registry,
    )

    errors = sorted(
        validator.iter_errors(zine_data),
        key=lambda error: list(error.absolute_path),
    )

    if errors:
        print(f"INVALID ✗ {display_path(zine_path)}")

        for error in errors:
            location = ".".join(
                str(part) for part in error.absolute_path
            )

            if not location:
                location = "<root>"

            print(f"- {location}: {error.message}")

        return 1

    print(f"VALID ✓ {display_path(zine_path)}")
    return 0


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: python scripts/validate_zine.py [zine.yaml]")
        return 2

    if len(sys.argv) == 2:
        zine_path = Path(sys.argv[1])

        if not zine_path.is_absolute():
            zine_path = ROOT / zine_path
    else:
        zine_path = DEFAULT_ZINE_PATH

    if not zine_path.exists():
        print(f"ERROR: File not found: {display_path(zine_path)}")
        return 2

    try:
        return validate_zine(zine_path)

    except (json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"ERROR: Unable to parse file: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

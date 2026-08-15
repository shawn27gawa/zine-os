#!/usr/bin/env python3

import json
import sys
from pathlib import Path, PurePath


FORMAT = "zineos-asset-placement"
VERSION = 1
PLACEMENT_MODES = ("desktop", "mobile")
NUMERIC_RANGES = {
    "x": (0, 100),
    "y": (0, 100),
    "scale": (0.5, 2.5),
    "frameX": (0, 100),
    "frameY": (0, 100),
    "frameSize": (10, 80),
}


def validate_settings(settings, path, errors):
    if not isinstance(settings, dict):
        errors.append(f"{path} must be an object")
        return

    if settings.get("fit") not in {"cover", "contain"}:
        errors.append(f"{path}.fit must be cover or contain")

    for field, (minimum, maximum) in NUMERIC_RANGES.items():
        value = settings.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{path}.{field} must be numeric")
        elif not minimum <= value <= maximum:
            errors.append(
                f"{path}.{field} must be between {minimum} and {maximum}"
            )


def validate_manifest_data(data):
    errors = []

    if not isinstance(data, dict):
        return ["manifest must be an object"]

    if data.get("format") != FORMAT:
        errors.append(f"format must be {FORMAT}")

    if data.get("version") != VERSION:
        errors.append(f"version must be {VERSION}")

    if not isinstance(data.get("projectId"), str) or not data.get("projectId"):
        errors.append("projectId must be a non-empty string")

    placements = data.get("placements")
    if not isinstance(placements, list):
        errors.append("placements must be an array")
        return errors

    seen_keys = set()

    for index, placement in enumerate(placements):
        path = f"placements[{index}]"

        if not isinstance(placement, dict):
            errors.append(f"{path} must be an object")
            continue

        key = placement.get("key")
        if not isinstance(key, str) or not key:
            errors.append(f"{path}.key must be a non-empty string")
        elif key in seen_keys:
            errors.append(f"{path}.key duplicates {key}")
        else:
            seen_keys.add(key)

        if placement.get("kind") not in {"asset", "memory-cell", "free-layer"}:
            errors.append(f"{path}.kind is unsupported")

        source = placement.get("source")
        if source is not None:
            if not isinstance(source, dict):
                errors.append(f"{path}.source must be an object or null")
            else:
                source_name = source.get("name")
                if not isinstance(source_name, str) or not source_name:
                    errors.append(f"{path}.source.name must be a non-empty string")
                elif PurePath(source_name).name != source_name:
                    errors.append(f"{path}.source.name must not contain a path")

        settings = placement.get("settings")
        if not isinstance(settings, dict):
            errors.append(f"{path}.settings must be an object")
            continue

        for mode in PLACEMENT_MODES:
            validate_settings(settings.get(mode), f"{path}.settings.{mode}", errors)

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_asset_placement.py manifest.json")
        return 2

    manifest_path = Path(sys.argv[1])

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        return 2

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: Unable to read manifest: {error}")
        return 2

    errors = validate_manifest_data(data)

    if errors:
        for error in errors:
            print(f"INVALID: {error}")
        return 1

    print(f"ASSET PLACEMENT VALID ✓ {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

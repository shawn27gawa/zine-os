#!/usr/bin/env python3

import json
import re
import sys
from pathlib import Path, PurePath


FORMAT = "zineos-text-placement"
VERSION = 1
FIELD_PATTERN = re.compile(r"^(content|caption|title|items\[[0-9]+\]\.text)$")
TYPOGRAPHY_RANGES = {
    "font_size_px": (6, 96),
    "line_height": (0.8, 4),
    "width_percent": (10, 100),
    "x_mm": (-100, 100),
    "y_mm": (-100, 100),
    "columns": (1, 4),
    "rule_spacing_mm": (1, 100),
}


def validate_source_reference(data, errors):
    reference = data.get("sourceReference")
    if not isinstance(reference, dict):
        errors.append("sourceReference must be an object")
        return

    digest = reference.get("zineSha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        errors.append("sourceReference.zineSha256 must be lowercase SHA-256")


def validate_typography(data, path, errors):
    if data is None:
        return
    if not isinstance(data, dict):
        errors.append(f"{path} must be an object or null")
        return

    unknown = set(data) - set(TYPOGRAPHY_RANGES)
    if unknown:
        errors.append(f"{path} contains unsupported fields: {sorted(unknown)}")

    for field, value in data.items():
        if field not in TYPOGRAPHY_RANGES:
            continue
        if value is None and field == "rule_spacing_mm":
            continue
        minimum, maximum = TYPOGRAPHY_RANGES[field]
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

    zine_path = data.get("zinePath")
    if not isinstance(zine_path, str) or not zine_path:
        errors.append("zinePath must be a non-empty string")
    elif PurePath(zine_path).is_absolute() or ".." in PurePath(zine_path).parts:
        errors.append("zinePath must be a safe repository-relative path")

    validate_source_reference(data, errors)
    edits = data.get("edits")
    if not isinstance(edits, list):
        errors.append("edits must be an array")
        return errors

    seen = set()
    seen_targets = set()
    for index, edit in enumerate(edits):
        path = f"edits[{index}]"
        if not isinstance(edit, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in ("key", "pageUnitId", "blockId", "originalText", "text"):
            if not isinstance(edit.get(field), str):
                errors.append(f"{path}.{field} must be a string")
        field = edit.get("field", "content")
        if not isinstance(field, str) or not FIELD_PATTERN.fullmatch(field):
            errors.append(f"{path}.field is unsupported")
        key = edit.get("key")
        if isinstance(key, str):
            if key in seen:
                errors.append(f"{path}.key duplicates {key}")
            seen.add(key)
        target = (edit.get("pageUnitId"), edit.get("blockId"), field)
        if all(isinstance(part, str) for part in target):
            if target in seen_targets:
                errors.append(f"{path} duplicates target {target}")
            else:
                seen_targets.add(target)
        validate_typography(edit.get("typography"), f"{path}.typography", errors)
    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_text_placement.py manifest.json")
        return 2
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: Unable to read manifest: {error}")
        return 2
    errors = validate_manifest_data(data)
    if errors:
        for error in errors:
            print(f"INVALID: {error}")
        return 1
    print(f"TEXT PLACEMENT VALID ✓ {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

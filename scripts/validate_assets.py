#!/usr/bin/env python3

"""Validate publication asset references without changing source files."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys

import yaml

from bootstrap_project import detect_image_format


RASTER_FORMATS = {
    ".gif": "GIF",
    ".jpeg": "JPEG",
    ".jpg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}


def exact_case_path(root, relative):
    current = root
    for part in PurePosixPath(relative).parts:
        if not current.is_dir():
            return None, "missing"
        names = {entry.name for entry in current.iterdir()}
        if part in names:
            current = current / part
            continue
        if any(name.casefold() == part.casefold() for name in names):
            return None, "case-mismatch"
        return None, "missing"
    return current, None


def is_safe_relative_source(source):
    if not isinstance(source, str) or not source:
        return False
    if "\\" in source:
        return False
    path = PurePosixPath(source)
    return not path.is_absolute() and ".." not in path.parts


def actual_format(path):
    suffix = path.suffix.lower()
    if suffix in RASTER_FORMATS:
        return detect_image_format(path)
    if suffix == ".svg":
        prefix = path.read_bytes()[:4096].lstrip()
        if prefix.startswith(b"<?xml"):
            prefix = re.sub(br"^<\?xml[^>]*>\s*", b"", prefix, count=1)
        return "SVG" if prefix.startswith(b"<svg") else "UNKNOWN"
    return None


def expected_format(path):
    if path.suffix.lower() == ".svg":
        return "SVG"
    return RASTER_FORMATS.get(path.suffix.lower())


def layout_asset_references(value, path="layout.settings"):
    references = []
    if isinstance(value, list):
        for index, item in enumerate(value):
            references.extend(layout_asset_references(item, f"{path}[{index}]"))
        return references
    if not isinstance(value, dict):
        return references
    for key, item in value.items():
        location = f"{path}.{key}"
        asset_key = key == "asset" or key.endswith("_asset")
        assets_key = key == "assets" or key.endswith("_assets")
        if asset_key and isinstance(item, str):
            references.append((item, location))
        elif assets_key and isinstance(item, list):
            references.extend(
                (asset_id, f"{location}[{index}]")
                for index, asset_id in enumerate(item)
                if isinstance(asset_id, str)
            )
        elif isinstance(item, dict):
            references.extend(layout_asset_references(item, location))
        elif isinstance(item, list) and not assets_key:
            references.extend(layout_asset_references(item, location))
    return references


def publication_asset_references(data):
    references = []
    for page_index, page in enumerate(data.get("pages", [])):
        page_id = page.get("id", f"pages[{page_index}]")
        for block_index, block in enumerate(page.get("blocks", [])):
            block_id = block.get("id", f"blocks[{block_index}]")
            prefix = f"{page_id}.{block_id}"
            if isinstance(block.get("asset"), str):
                references.append((block["asset"], f"{prefix}.asset"))
            if isinstance(block.get("assets"), list):
                references.extend(
                    (asset_id, f"{prefix}.assets[{index}]")
                    for index, asset_id in enumerate(block["assets"])
                    if isinstance(asset_id, str)
                )
        references.extend(
            layout_asset_references(
                page.get("layout", {}).get("settings", {}),
                f"{page_id}.layout.settings",
            )
        )
    return references


def validate_asset_integrity(zine_path):
    zine_path = Path(zine_path).resolve()
    try:
        data = yaml.safe_load(zine_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        return {
            "status": "FAIL",
            "zine": str(zine_path),
            "assets": 0,
            "references": 0,
            "errors": [f"Unable to read publication: {error}"],
            "warnings": [],
        }

    errors = []
    warnings = []
    assets = data.get("assets", []) if isinstance(data, dict) else []
    by_id = {}
    zine_directory = zine_path.parent.resolve()
    references = publication_asset_references(data if isinstance(data, dict) else {})
    referenced_ids = {asset_id for asset_id, _ in references}
    unused_with_issue = set()

    def asset_issue(asset_id, message):
        if asset_id in referenced_ids:
            errors.append(message)
        else:
            warnings.append(f"Unused asset issue: {message}")
            unused_with_issue.add(asset_id)

    for index, asset in enumerate(assets):
        asset_id = asset.get("id") if isinstance(asset, dict) else None
        location = f"assets[{index}]"
        if not isinstance(asset_id, str) or not asset_id:
            errors.append(f"{location}: asset ID is missing")
            continue
        if asset_id in by_id:
            errors.append(f"{location}: duplicate asset ID: {asset_id}")
            continue
        by_id[asset_id] = asset
        source = asset.get("source")
        if not is_safe_relative_source(source):
            asset_issue(
                asset_id,
                f"{location} ({asset_id}): unsafe asset source: {source!r}",
            )
            continue
        source_path, path_error = exact_case_path(zine_directory, source)
        if path_error == "case-mismatch":
            asset_issue(
                asset_id,
                f"{location} ({asset_id}): filename case mismatch: {source}",
            )
            continue
        if path_error or source_path is None or not source_path.is_file():
            asset_issue(
                asset_id,
                f"{location} ({asset_id}): asset file is missing: {source}",
            )
            continue
        try:
            source_path.resolve().relative_to(zine_directory)
        except ValueError:
            asset_issue(
                asset_id,
                f"{location} ({asset_id}): asset resolves outside publication: {source}",
            )
            continue
        expected = expected_format(source_path)
        if expected:
            detected = actual_format(source_path)
            if detected != expected:
                asset_issue(
                    asset_id,
                    f"{location} ({asset_id}): extension expects {expected}, "
                    f"but file data is {detected}: {source}",
                )

    for asset_id, location in references:
        if asset_id not in by_id:
            errors.append(f"{location}: unknown asset reference: {asset_id}")

    for asset_id in sorted(set(by_id) - referenced_ids - unused_with_issue):
        warnings.append(f"Unused asset is retained: {asset_id}")

    return {
        "status": "PASS" if not errors else "FAIL",
        "zine": str(zine_path),
        "assets": len(by_id),
        "references": len(references),
        "errors": errors,
        "warnings": warnings,
    }


def print_report(report):
    print(
        f"ASSET {report['status']}: {report['assets']} assets, "
        f"{report['references']} references"
    )
    for error in report["errors"]:
        print(f"ERROR: {error}")
    for warning in report["warnings"]:
        print(f"WARNING: {warning}")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Validate ZineOS publication assets.")
    parser.add_argument("zine", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    report = validate_asset_integrity(args.zine)
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

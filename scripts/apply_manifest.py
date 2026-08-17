#!/usr/bin/env python3

import argparse
from copy import deepcopy
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePath
import re
import shutil
import tempfile

import yaml

from validate_asset_placement import validate_manifest_data as validate_asset
from validate_text_placement import validate_manifest_data as validate_text


ROOT = Path(__file__).resolve().parents[1]


class ManifestError(ValueError):
    pass


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def node_pairs(mapping_node):
    return {key.value: (key, value) for key, value in mapping_node.value}


def flow_yaml(value):
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=True,
        sort_keys=False,
        width=100000,
    ).strip()


def quoted(value):
    return json.dumps(value, ensure_ascii=False)


def literal_scalar(value, column):
    indent = " " * (column + 2)
    if value.endswith("\n\n"):
        indicator = "|+"
    elif value.endswith("\n"):
        indicator = "|"
    else:
        indicator = "|-"
    lines = value.splitlines()
    rendered = f"{indicator}\n"
    for line in lines:
        rendered += f"{indent}{line}\n" if line else f"{indent}\n"
    return rendered


def replace_mapping_value(replacements, pairs, key, value):
    if key not in pairs:
        raise ManifestError(f"Expected YAML field is missing: {key}")
    node = pairs[key][1]
    replacements.append((node.start_mark.index, node.end_mark.index, value))


def set_mapping_field(replacements, mapping_node, key, value, child_indent):
    pairs = node_pairs(mapping_node)
    rendered = flow_yaml(value)
    if key in pairs:
        node = pairs[key][1]
        if isinstance(node, (yaml.SequenceNode, yaml.MappingNode)) and not node.flow_style:
            rendered += "\n" + " " * node.end_mark.column
        replacements.append((node.start_mark.index, node.end_mark.index, rendered))
    else:
        insertion = f"{' ' * child_indent}{key}: {rendered}\n"
        insertion_at = mapping_node.start_mark.index - mapping_node.start_mark.column
        replacements.append((insertion_at, insertion_at, insertion))


def set_block_metadata(replacements, block_node, metadata):
    pairs = node_pairs(block_node)
    rendered = flow_yaml(metadata)
    if "metadata" in pairs:
        node = pairs["metadata"][1]
        replacements.append((node.start_mark.index, node.end_mark.index, rendered))
    else:
        indent = block_node.start_mark.column
        insertion = f"{' ' * indent}metadata: {rendered}\n"
        insertion_at = block_node.end_mark.index - block_node.end_mark.column
        replacements.append((insertion_at, insertion_at, insertion))


def set_layout_setting(replacements, page_node, key, value):
    page_pairs = node_pairs(page_node)
    if "layout" not in page_pairs:
        raise ManifestError("Target page has no layout")
    layout_node = page_pairs["layout"][1]
    layout_pairs = node_pairs(layout_node)
    if "settings" in layout_pairs:
        settings_node = layout_pairs["settings"][1]
        set_mapping_field(
            replacements,
            settings_node,
            key,
            value,
            child_indent=layout_pairs["settings"][0].start_mark.column + 2,
        )
    else:
        indent = page_pairs["layout"][0].start_mark.column + 2
        insertion = (
            f"{' ' * indent}settings:\n"
            f"{' ' * (indent + 2)}{key}: {flow_yaml(value)}\n"
        )
        insertion_at = layout_node.end_mark.index - layout_node.end_mark.column
        replacements.append((insertion_at, insertion_at, insertion))


def apply_replacements(source, replacements):
    occupied = []
    for start, end, _ in sorted(replacements):
        if occupied and start < occupied[-1][1]:
            raise ManifestError("Manifest changes overlap; split the handoff")
        occupied.append((start, end))
    result = source
    for start, end, value in sorted(replacements, reverse=True):
        result = result[:start] + value + result[end:]
    return result


def safe_repo_path(value):
    pure = PurePath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"Unsafe repository path: {value}")
    path = (ROOT / pure).resolve()
    if ROOT not in path.parents:
        raise ManifestError(f"Path escapes repository: {value}")
    return path


def exact_source_file(asset_dir, name):
    matches = {entry.name: entry for entry in asset_dir.iterdir() if entry.is_file()}
    if name not in matches:
        raise ManifestError(f"Source asset not found with exact filename case: {name}")
    return matches[name]


def slug(value):
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "image"


def allocate_asset_id(filename, existing):
    base = f"studio-{slug(Path(filename).stem)}"
    candidate = base
    number = 2
    while candidate in existing:
        candidate = f"{base}-{number}"
        number += 1
    existing.add(candidate)
    return candidate


def build_indexes(data, root_node):
    root_pairs = node_pairs(root_node)
    page_nodes = {}
    block_nodes = {}
    for page_node in root_pairs["pages"][1].value:
        pairs = node_pairs(page_node)
        page_id = pairs["id"][1].value
        page_nodes[page_id] = (page_node, pairs)
        for block_node in pairs["blocks"][1].value:
            block_pairs = node_pairs(block_node)
            block_id = block_pairs.get("id", (None, None))[1]
            if block_id:
                block_nodes[(page_id, block_id.value)] = (block_node, block_pairs)
    pages = {page["id"]: page for page in data["pages"]}
    assets = {asset["id"]: asset for asset in data["assets"]}
    return root_pairs, pages, assets, page_nodes, block_nodes


def validate_target(manifest, zine_path, raw, data):
    expected_path = safe_repo_path(manifest["zinePath"])
    if expected_path != zine_path.resolve():
        raise ManifestError(
            f"Manifest targets {expected_path}, not {zine_path.resolve()}"
        )
    if manifest["projectId"] != data.get("project", {}).get("id"):
        raise ManifestError("Manifest projectId does not match publication")
    actual_hash = sha256_bytes(raw)
    expected_hash = manifest["sourceReference"]["zineSha256"]
    if actual_hash != expected_hash:
        raise ManifestError(
            "Publication source changed since export: "
            f"expected {expected_hash}, found {actual_hash}"
        )


def text_field_target(block, pairs, field):
    if field in {"content", "caption", "title"}:
        if field not in pairs or not isinstance(block.get(field), str):
            raise ManifestError(f"Target block has no inline field: {field}")
        return block[field], pairs[field][1]

    match = re.fullmatch(r"items\[([0-9]+)]\.text", field)
    if not match or "items" not in pairs:
        raise ManifestError(f"Unsupported text field: {field}")
    index = int(match.group(1))
    items = block.get("items", [])
    sequence = pairs["items"][1]
    if not 0 <= index < len(items) or not 0 <= index < len(sequence.value):
        raise ManifestError(f"Text item is outside target Block: {field}")
    item_pairs = node_pairs(sequence.value[index])
    if "text" not in item_pairs or not isinstance(items[index].get("text"), str):
        raise ManifestError(f"Target item has no text field: {field}")
    return items[index]["text"], item_pairs["text"][1]


def apply_text_manifest(manifest, data, indexes, replacements):
    _, pages, _, _, block_nodes = indexes
    block_updates = {}
    for edit in manifest["edits"]:
        page_id = edit["pageUnitId"]
        block_id = edit["blockId"]
        field = edit.get("field", "content")
        if page_id not in pages or (page_id, block_id) not in block_nodes:
            raise ManifestError(f"Text target not found: {page_id}/{block_id}")
        block = next(
            block for block in pages[page_id]["blocks"] if block.get("id") == block_id
        )
        block_node, pairs = block_nodes[(page_id, block_id)]
        current_text, content_node = text_field_target(block, pairs, field)
        if current_text != edit["originalText"]:
            raise ManifestError(f"Original text mismatch: {page_id}/{block_id}/{field}")
        replacements.append((
            content_node.start_mark.index,
            content_node.end_mark.index,
            literal_scalar(edit["text"], content_node.start_mark.column),
        ))
        if edit.get("typography") is not None:
            metadata = deepcopy(
                block_updates.get(
                    (page_id, block_id),
                    (None, block.get("metadata", {})),
                )[1]
            )
            studio = metadata.setdefault("zineos_studio", {})
            studio.setdefault("text_placements", {})[field] = edit["typography"]
            block_updates[(page_id, block_id)] = (block_node, metadata)
    for block_node, metadata in block_updates.values():
        set_block_metadata(replacements, block_node, metadata)
    return []


def replace_block_asset(replacements, block_pairs, placement, new_asset_id):
    if "asset" in block_pairs:
        if block_pairs["asset"][1].value != placement["assetId"]:
            raise ManifestError("Block asset reference changed since export")
        replace_mapping_value(replacements, block_pairs, "asset", quoted(new_asset_id))
        return
    if "assets" not in block_pairs:
        raise ManifestError(f"Block has no asset reference: {placement['blockId']}")
    sequence = block_pairs["assets"][1]
    index = placement.get("assetIndex")
    if not isinstance(index, int) or not 0 <= index < len(sequence.value):
        raise ManifestError("Gallery placement has an invalid assetIndex")
    node = sequence.value[index]
    if node.value != placement["assetId"]:
        raise ManifestError("Gallery asset reference changed since export")
    replacements.append((node.start_mark.index, node.end_mark.index, quoted(new_asset_id)))


def append_asset_records(replacements, assets_node, records):
    if not records:
        return
    item_indent = (
        max(0, assets_node.value[0].start_mark.column - 2)
        if assets_node.value
        else assets_node.start_mark.column
    )
    field_indent = item_indent + 2
    lines = []
    for record in records:
        lines.extend([
            f'{" " * item_indent}- id: {quoted(record["id"])}',
            f'{" " * field_indent}type: "image"',
            f'{" " * field_indent}source: {quoted(record["source"])}',
            f'{" " * field_indent}title: {quoted(record["title"])}',
            "",
        ])
    replacements.append((
        assets_node.end_mark.index - assets_node.end_mark.column,
        assets_node.end_mark.index - assets_node.end_mark.column,
        "\n".join(lines),
    ))


def apply_asset_manifest(manifest, data, indexes, replacements, asset_dir, zine_path):
    root_pairs, pages, assets, page_nodes, block_nodes = indexes
    existing_ids = set(assets)
    records = []
    copies = []
    block_updates = {}
    page_placements = {}
    memory_assets = {}
    planned_destinations = set()

    for placement in manifest["placements"]:
        if placement["kind"] == "free-layer":
            raise ManifestError(
                "Free-layer application requires an explicit Block; add one before apply"
            )
        page_id = placement["pageUnitId"]
        if page_id not in pages:
            raise ManifestError(f"Page target not found: {page_id}")
        source = placement.get("source")
        target_asset_id = placement.get("assetId")

        if source:
            if asset_dir is None:
                raise ManifestError("--asset-dir is required for source image changes")
            source_path = exact_source_file(asset_dir, source["name"])
            if source_path.stat().st_size != source["size"]:
                raise ManifestError(
                    f"Source asset size changed since export: {source['name']}"
                )
            target_asset_id = allocate_asset_id(source["name"], existing_ids)
            relative_source = f"assets/{source['name']}"
            destination = zine_path.parent / relative_source
            if destination.exists():
                if sha256_bytes(destination.read_bytes()) != sha256_bytes(
                    source_path.read_bytes()
                ):
                    raise ManifestError(
                        f"Destination exists with different content: {destination}"
                    )
            else:
                if destination not in planned_destinations:
                    copies.append((source_path, destination))
                    planned_destinations.add(destination)
            records.append({
                "id": target_asset_id,
                "source": relative_source,
                "title": Path(source["name"]).stem,
            })

        if placement["kind"] == "asset":
            key = (page_id, placement["blockId"])
            if key not in block_nodes:
                raise ManifestError(f"Asset target not found: {key[0]}/{key[1]}")
            block_node, block_pairs = block_nodes[key]
            block = next(
                block for block in pages[page_id]["blocks"]
                if block.get("id") == placement["blockId"]
            )
            if "asset" in block_pairs:
                current_asset_id = block.get("asset")
            else:
                asset_index = placement.get("assetIndex")
                block_assets = block.get("assets", [])
                if not isinstance(asset_index, int) or not 0 <= asset_index < len(
                    block_assets
                ):
                    raise ManifestError("Gallery placement has an invalid assetIndex")
                current_asset_id = block_assets[asset_index]
            if current_asset_id != placement["assetId"]:
                raise ManifestError("Block asset reference changed since export")
            if source:
                replace_block_asset(replacements, block_pairs, placement, target_asset_id)
            metadata = deepcopy(
                block_updates.get(key, (None, block.get("metadata", {})))[1]
            )
            studio = metadata.setdefault("zineos_studio", {})
            studio.setdefault("asset_placements", {})[target_asset_id] = placement[
                "settings"
            ]
            block_updates[key] = (block_node, metadata)
        else:
            cell_index = placement["cellIndex"]
            layout = pages[page_id].setdefault("layout", {})
            current = memory_assets.setdefault(
                page_id,
                list(layout.get("settings", {}).get("assets", [])),
            )
            if not 0 <= cell_index < len(current):
                raise ManifestError(f"Memory cell is outside configured grid: {cell_index}")
            if current[cell_index] != placement["assetId"]:
                raise ManifestError("Memory-cell asset reference changed since export")
            if source:
                current[cell_index] = target_asset_id
            page_placements.setdefault(page_id, {})[target_asset_id] = placement[
                "settings"
            ]

    for block_node, metadata in block_updates.values():
        set_block_metadata(replacements, block_node, metadata)
    for page_id, assets_list in memory_assets.items():
        set_layout_setting(replacements, page_nodes[page_id][0], "assets", assets_list)
    for page_id, placements in page_placements.items():
        set_layout_setting(
            replacements,
            page_nodes[page_id][0],
            "asset_placements",
            placements,
        )
    append_asset_records(replacements, root_pairs["assets"][1], records)
    return copies


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate and safely apply a ZineOS Studio manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--zine", type=Path)
    parser.add_argument("--asset-dir", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the validated change. Without this flag, only show the diff.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        validators = {
            "zineos-asset-placement": validate_asset,
            "zineos-text-placement": validate_text,
        }
        validator = validators.get(manifest.get("format"))
        if validator is None:
            raise ManifestError("Unsupported manifest format")
        errors = validator(manifest)
        if errors:
            raise ManifestError("; ".join(errors))

        zine_path = (
            args.zine.resolve()
            if args.zine
            else safe_repo_path(manifest["zinePath"])
        )
        raw = zine_path.read_bytes()
        source = raw.decode("utf-8")
        data = yaml.safe_load(source)
        root_node = yaml.compose(source)
        validate_target(manifest, zine_path, raw, data)
        indexes = build_indexes(data, root_node)
        replacements = []
        asset_dir = args.asset_dir.resolve() if args.asset_dir else None

        if manifest["format"] == "zineos-text-placement":
            copies = apply_text_manifest(manifest, data, indexes, replacements)
        else:
            copies = apply_asset_manifest(
                manifest, data, indexes, replacements, asset_dir, zine_path
            )
        updated = apply_replacements(source, replacements)
        yaml.safe_load(updated)
    except (OSError, json.JSONDecodeError, yaml.YAMLError, ManifestError) as error:
        print(f"ERROR: {error}")
        return 2

    diff = "".join(difflib.unified_diff(
        source.splitlines(keepends=True),
        updated.splitlines(keepends=True),
        fromfile=str(zine_path),
        tofile=str(zine_path),
    ))
    for source_path, destination in copies:
        print(f"COPY: {source_path} -> {destination}")
    print(diff or "NO CHANGES")

    if not args.apply:
        print("DRY RUN PASS: no files written; use --apply after reviewing this diff")
        return 0

    for source_path, destination in copies:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temp:
            temporary = Path(temp.name)
        try:
            shutil.copy2(source_path, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=zine_path.parent, delete=False
    ) as temp:
        temp.write(updated)
        temporary_zine = Path(temp.name)
    os.replace(temporary_zine, zine_path)
    print(f"APPLY PASS: {zine_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

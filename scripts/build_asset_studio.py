#!/usr/bin/env python3

import base64
import hashlib
import html
import json
import subprocess
import sys
from pathlib import Path

import yaml

from build_preview import ROOT, build_html, load_yaml


DEFAULT_ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"
DEFAULT_OUTPUT_PATH = ROOT / "preview" / "ZINE_001_STUDIO.html"
STUDIO_DIR = ROOT / "studio"


def source_reference(zine_path):
    try:
        git_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = None

    return {
        "gitCommit": git_commit,
        "zineSha256": hashlib.sha256(zine_path.read_bytes()).hexdigest(),
    }


def encode_text(value):
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def editable_asset_slots(page_unit, article_index):
    slots = []
    layout_settings = page_unit.get("layout", {}).get("settings", {})
    default_position = layout_settings.get("image_position")

    for block_index, block in enumerate(page_unit.get("blocks", [])):
        block_type = block.get("type")
        block_id = block.get("id", f"block-{block_index + 1}")

        if block_type in {"PHOTO", "CLOSEUP"}:
            asset_id = block.get("asset")
            slots.append(
                {
                    "key": f"{page_unit['id']}:{block_id}:{asset_id}",
                    "kind": "asset",
                    "label": block.get("role") or asset_id or block_type,
                    "articleIndex": article_index,
                    "blockIndex": block_index,
                    "assetIndex": 0,
                    "blockId": block_id,
                    "assetId": asset_id,
                    "defaultPosition": default_position,
                }
            )

        elif block_type == "GALLERY":
            for asset_index, asset_id in enumerate(block.get("assets", [])):
                slots.append(
                    {
                        "key": f"{page_unit['id']}:{block_id}:{asset_id}",
                        "kind": "asset",
                        "label": asset_id,
                        "articleIndex": article_index,
                        "blockIndex": block_index,
                        "assetIndex": asset_index,
                        "blockId": block_id,
                        "assetId": asset_id,
                        "defaultPosition": default_position,
                    }
                )

    return slots


def memory_grid_slots(page_unit, article_index):
    layout = page_unit.get("layout", {})
    layout_type = layout.get("type")

    if layout_type not in {"memory-index-grid", "closing-memory-grid"}:
        return []

    settings = layout.get("settings", {})
    rows = int(settings.get("rows", 4))
    columns = int(settings.get("columns", 5))
    image_assets = settings.get("assets", [])

    return [
        {
            "key": f"{page_unit['id']}:memory-cell:{index}",
            "kind": "memory-cell",
            "label": f"Memory cell {index}",
            "articleIndex": article_index,
            "cellIndex": index - 1,
            "assetId": (
                image_assets[index - 1]
                if index <= len(image_assets)
                else None
            ),
            "monochrome": True,
        }
        for index in range(1, rows * columns + 1)
    ]


def virtual_layout_slots(page_unit, article_index):
    layout_type = page_unit.get("layout", {}).get("type")

    if layout_type != "recipe-page":
        return []

    image_blocks = [
        block
        for block in page_unit.get("blocks", [])
        if block.get("type") in {"PHOTO", "CLOSEUP"} and block.get("asset")
    ]
    if len(image_blocks) >= 2:
        return []

    return [
        {
            "key": f"{page_unit['id']}:virtual:secondary-image",
            "kind": "free-layer",
            "label": "Secondary image layer",
            "articleIndex": article_index,
            "role": "secondary-image",
            "defaultFit": "contain",
            "frame": {
                "x": 72,
                "y": 64,
                "size": 30,
            },
        }
    ]


def editable_text_slots(page_unit, article_index):
    slots = []

    for block_index, block in enumerate(page_unit.get("blocks", [])):
        block_id = block.get("id", f"block-{block_index + 1}")
        block_type = block.get("type", "TEXT")
        studio = block.get("metadata", {}).get("zineos_studio", {})
        placements = studio.get("text_placements", {})

        def add_slot(field, value, label):
            typography = placements.get(field)
            if field == "content" and typography is None:
                typography = studio.get("text_placement")
            slots.append({
                "key": f"{page_unit['id']}:{block_id}:text:{field}",
                "kind": "text",
                "label": label,
                "articleIndex": article_index,
                "blockIndex": block_index,
                "blockId": block_id,
                "field": field,
                "originalText": value,
                "typography": typography,
            })

        if isinstance(block.get("content"), str):
            add_slot("content", block["content"], block_type)

        if isinstance(block.get("caption"), str):
            add_slot("caption", block["caption"], f"{block_type} caption")

        if block_type == "CHECKLIST":
            if isinstance(block.get("title"), str):
                add_slot("title", block["title"], "Checklist title")
            for item_index, item in enumerate(block.get("items", [])):
                if isinstance(item.get("text"), str):
                    add_slot(
                        f"items[{item_index}].text",
                        item["text"],
                        f"Checklist item {item_index + 1}",
                    )

    return slots


def build_studio_config(zine_data, zine_path):
    page_units = []

    for article_index, page_unit in enumerate(zine_data.get("pages", [])):
        slots = editable_asset_slots(page_unit, article_index)
        slots.extend(memory_grid_slots(page_unit, article_index))
        slots.extend(virtual_layout_slots(page_unit, article_index))
        text_slots = editable_text_slots(page_unit, article_index)

        page_units.append(
            {
                "id": page_unit.get("id"),
                "pages": page_unit.get("pages", []),
                "layoutType": page_unit.get("layout", {}).get("type", "default"),
                "articleIndex": article_index,
                "slots": slots,
                "textSlots": text_slots,
            }
        )

    project = zine_data.get("project", {})

    return {
        "format": "zineos-unified-studio",
        "version": 1,
        "project": {
            "id": project.get("id"),
            "title": project.get("title", "Untitled Zine"),
        },
        "zinePath": str(zine_path.relative_to(ROOT)),
        "sourceReference": source_reference(zine_path),
        "pageUnits": page_units,
    }


def build_studio_html(zine_data, zine_path, output_path):
    preview_html = build_html(zine_data, zine_path, output_path)
    config = build_studio_config(zine_data, zine_path)
    studio_css = (STUDIO_DIR / "asset-placement.css").read_text(encoding="utf-8")
    studio_js = (STUDIO_DIR / "asset-placement.js").read_text(encoding="utf-8")
    title = html.escape(config["project"]["title"])

    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title} — ZineOS Unified Studio</title>
    <style>{studio_css}</style>
</head>
<body>
    <header class="studio-toolbar">
        <div>
            <strong>ZineOS Unified Studio</strong>
            <span class="studio-project">{title}</span>
        </div>
        <div class="studio-toolbar-actions">
            <label class="studio-button">
                Import manifest
                <input id="manifest-import" type="file" accept="application/json,.json">
            </label>
            <button id="asset-manifest-export" type="button">Export images</button>
            <button id="text-manifest-export" type="button">Export text</button>
        </div>
    </header>

    <div class="studio-shell">
        <nav class="studio-pages" aria-label="Publication pages">
            <h2>Pages</h2>
            <div id="page-navigation"></div>
        </nav>

        <main class="studio-canvas">
            <div class="studio-modes" aria-label="Preview mode">
                <button type="button" data-mode="desktop" class="is-active">Desktop</button>
                <button type="button" data-mode="mobile">Mobile</button>
                <button type="button" data-mode="print">Print</button>
            </div>
            <div id="studio-message" role="status">
                Select outlined text or drop a photograph onto an image slot.
            </div>
            <div id="preview-frame-wrap" class="mode-desktop">
                <iframe id="preview-frame" title="Editable ZineOS preview"></iframe>
            </div>
        </main>

        <aside class="studio-inspector">
            <h2 id="inspector-title">Edit</h2>
            <p id="selection-label">Select an image or text slot.</p>

            <div id="placement-controls" hidden>
                <label class="studio-button studio-file-picker">
                    Choose image(s)
                    <input id="slot-file-input" type="file" accept="image/*" multiple>
                </label>

                <dl class="studio-file-meta">
                    <dt>File</dt>
                    <dd id="selection-file">Not assigned</dd>
                </dl>

                <label>
                    Fit
                    <select id="placement-fit">
                        <option value="cover">Cover</option>
                        <option value="contain">Contain</option>
                    </select>
                </label>

                <label>
                    Horizontal position <output id="placement-x-output">50%</output>
                    <input id="placement-x" type="range" min="0" max="100" value="50">
                </label>

                <label>
                    Vertical position <output id="placement-y-output">50%</output>
                    <input id="placement-y" type="range" min="0" max="100" value="50">
                </label>

                <label>
                    Scale <output id="placement-scale-output">1.00×</output>
                    <input id="placement-scale" type="range" min="0.5" max="2.5" step="0.01" value="1">
                </label>

                <fieldset id="free-layer-controls" hidden>
                    <legend>Layer frame</legend>
                    <label>
                        Page X <output id="frame-x-output">72%</output>
                        <input id="frame-x" type="range" min="0" max="100" value="72">
                    </label>
                    <label>
                        Page Y <output id="frame-y-output">64%</output>
                        <input id="frame-y" type="range" min="0" max="100" value="64">
                    </label>
                    <label>
                        Frame size <output id="frame-size-output">30%</output>
                        <input id="frame-size" type="range" min="10" max="80" value="30">
                    </label>
                </fieldset>

                <button id="placement-reset" type="button" class="studio-secondary">Reset current mode</button>
            </div>

            <div id="text-controls" hidden>
                <label>
                    Text
                    <textarea id="text-content" rows="10"></textarea>
                </label>

                <label>
                    Font size <output id="text-font-size-output"></output>
                    <input id="text-font-size" type="range" min="6" max="96" step="0.25">
                </label>

                <label>
                    Line height <output id="text-line-height-output"></output>
                    <input id="text-line-height" type="range" min="0.8" max="4" step="0.05">
                </label>

                <label>
                    Width <output id="text-width-output"></output>
                    <input id="text-width" type="range" min="10" max="100" step="1">
                </label>

                <label>
                    Horizontal offset <output id="text-x-output"></output>
                    <input id="text-x" type="range" min="-100" max="100" step="0.5">
                </label>

                <label>
                    Vertical offset <output id="text-y-output"></output>
                    <input id="text-y" type="range" min="-100" max="100" step="0.5">
                </label>

                <label>
                    Columns <output id="text-columns-output"></output>
                    <input id="text-columns" type="range" min="1" max="4" step="1">
                </label>

                <button id="text-reset" type="button" class="studio-secondary">Reset text edit</button>
            </div>

            <section class="studio-help">
                <h3>Safe workflow</h3>
                <p>Images and text edits remain in browser memory. Export a manifest for Builder review; this Studio never writes the repository.</p>
                <p>Memory-grid images are previewed in monochrome. Originals remain unchanged.</p>
            </section>

            <section id="manifest-handoff" class="studio-manifest" hidden>
                <h3 id="manifest-title">Builder manifest</h3>
                <textarea id="manifest-output" readonly aria-label="Builder manifest"></textarea>
                <a id="manifest-download" class="studio-button" download>Download JSON</a>
                <button id="manifest-copy" type="button" class="studio-secondary">Copy JSON</button>
            </section>
        </aside>
    </div>

    <script id="studio-config" type="application/octet-stream">{encode_text(json.dumps(config, ensure_ascii=False))}</script>
    <script id="preview-source" type="application/octet-stream">{encode_text(preview_html)}</script>
    <script>{studio_js}</script>
</body>
</html>
"""


def main():
    if len(sys.argv) > 3:
        print(
            "Usage: python scripts/build_asset_studio.py "
            "[zine.yaml] [output.html]"
        )
        return 2

    zine_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else DEFAULT_ZINE_PATH
    output_path = Path(sys.argv[2]) if len(sys.argv) == 3 else DEFAULT_OUTPUT_PATH

    if not zine_path.is_absolute():
        zine_path = ROOT / zine_path

    if not output_path.is_absolute():
        output_path = ROOT / output_path

    if not zine_path.exists():
        print(f"ERROR: Zine file not found: {zine_path}")
        return 2

    try:
        zine_data = load_yaml(zine_path)
    except yaml.YAMLError as error:
        print(f"ERROR: Unable to parse YAML: {error}")
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_studio_html(zine_data, zine_path, output_path),
        encoding="utf-8",
    )

    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path

    print(f"UNIFIED STUDIO ✓ {display_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

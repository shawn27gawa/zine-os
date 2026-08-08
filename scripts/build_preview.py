#!/usr/bin/env python3

import html
import os
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"
DEFAULT_OUTPUT_PATH = ROOT / "preview" / "ZINE_001.html"


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def escape(value):
    if value is None:
        return ""
    return html.escape(str(value))


def build_asset_index(zine_data):
    return {
        asset["id"]: asset
        for asset in zine_data.get("assets", [])
        if "id" in asset
    }


def resolve_asset_path(asset_id, assets, zine_dir, output_dir):
    asset = assets.get(asset_id)

    if not asset:
        return None, None

    source = asset.get("source")

    if not source:
        return asset, None

    source_path = zine_dir / source

    if not source_path.exists():
        return asset, None

    relative_path = os.path.relpath(source_path, output_dir)

    return asset, relative_path


def render_asset_visual(asset_id, assets, zine_dir, output_dir, label="IMAGE"):
    asset, relative_path = resolve_asset_path(
        asset_id,
        assets,
        zine_dir,
        output_dir,
    )

    title = asset.get("title", asset_id) if asset else asset_id

    if relative_path:
        return f"""
        <figure class="asset">
            <img src="{escape(relative_path)}" alt="{escape(title)}">
            <figcaption>{escape(title)}</figcaption>
        </figure>
        """

    return f"""
    <div class="asset-placeholder">
        <span class="asset-type">{escape(label)}</span>
        <strong>{escape(title)}</strong>
        <small>{escape(asset_id)}</small>
    </div>
    """


def render_memory_grid(layout):
    settings = layout.get("settings", {})

    rows = int(settings.get("rows", 4))
    columns = int(settings.get("columns", 5))

    filled_cells = set(settings.get("filled_cells", []))

    cells = []

    for index in range(1, rows * columns + 1):
        state = "filled" if index in filled_cells else "empty"

        cells.append(
            f'<div class="memory-cell {state}" '
            f'title="Memory cell {index}"></div>'
        )

    meaning = settings.get(
        "empty_cells_meaning",
        settings.get("relationship_to_opening", ""),
    )

    return f"""
    <div
        class="memory-grid"
        style="grid-template-columns: repeat({columns}, 1fr);"
    >
        {''.join(cells)}
    </div>
    <div class="memory-note">
        {escape(meaning)}
    </div>
    """


def render_checklist(block):
    items = []

    for item in block.get("items", []):
        checked = bool(item.get("checked", False))
        mark = "✓" if checked else "○"

        items.append(
            f"""
            <li class="checklist-item">
                <span class="checkmark">{mark}</span>
                <span>{escape(item.get("text", ""))}</span>
            </li>
            """
        )

    title = block.get("title")

    title_html = (
        f'<h4 class="block-title">{escape(title)}</h4>'
        if title
        else ""
    )

    return f"""
    {title_html}
    <ul class="checklist">
        {''.join(items)}
    </ul>
    """


def render_gallery(block, assets, zine_dir, output_dir):
    rendered_assets = []

    for asset_id in block.get("assets", []):
        rendered_assets.append(
            render_asset_visual(
                asset_id,
                assets,
                zine_dir,
                output_dir,
                label="PHOTO",
            )
        )

    return f"""
    <div class="gallery">
        {''.join(rendered_assets)}
    </div>
    """


def render_block(block, assets, zine_dir, output_dir):
    block_type = block.get("type", "UNKNOWN")

    content = ""

    if block_type == "PHOTO":
        content = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="PHOTO",
        )

    elif block_type == "MAP":
        content = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="MAP",
        )

    elif block_type == "GALLERY":
        content = render_gallery(
            block,
            assets,
            zine_dir,
            output_dir,
        )

    elif block_type == "CLOSEUP":
        asset_html = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="CLOSEUP",
        )

        region = block.get("region", {})

        region_text = (
            f"x={region.get('x', '?')}, "
            f"y={region.get('y', '?')}, "
            f"w={region.get('width', '?')}, "
            f"h={region.get('height', '?')}"
        )

        content = f"""
        {asset_html}
        <div class="technical-note">
            Crop region: {escape(region_text)}
        </div>
        """

    elif block_type == "CHECKLIST":
        content = render_checklist(block)

    elif block_type == "QUESTION":
        content = f"""
        <div class="question">
            {escape(block.get("content", ""))}
        </div>
        """

    elif block_type == "QUOTE":
        content = f"""
        <blockquote>
            {escape(block.get("content", ""))}
        </blockquote>
        """

    elif block_type in {"TEXT", "CAPTION"}:
        text = block.get("content", block.get("caption", ""))

        content = f"""
        <div class="text-content">
            {escape(text).replace(chr(10), "<br>")}
        </div>
        """

    elif block_type == "ESSAY":
        asset_id = block.get("asset")
        asset = assets.get(asset_id, {})
        source = asset.get("source")

        text = None

        if source:
            source_path = zine_dir / source

            if source_path.exists():
                text = source_path.read_text(encoding="utf-8")

        if text:
            content = f"""
            <div class="essay">
                {escape(text).replace(chr(10), "<br>")}
            </div>
            """
        else:
            content = f"""
            <div class="asset-placeholder">
                <span class="asset-type">ESSAY</span>
                <strong>{escape(asset.get("title", asset_id))}</strong>
                <small>{escape(asset_id)}</small>
            </div>
            """

    else:
        content = f"""
        <div class="unknown-block">
            Unsupported Block: {escape(block_type)}
        </div>
        """

    caption = block.get("caption")

    caption_html = (
        f'<div class="caption">{escape(caption)}</div>'
        if caption
        else ""
    )

    return f"""
    <section class="block block-{escape(block_type.lower())}">
        <div class="block-label">{escape(block_type)}</div>
        {content}
        {caption_html}
    </section>
    """

def render_page_unit(page_unit, assets, zine_dir, output_dir):
    pages = page_unit.get("pages", [])
    layout = page_unit.get("layout", {})

    layout_type = layout.get("type", "unspecified")

    layout_slug = "".join(
        character
        if character.isalnum() or character == "-"
        else "-"
        for character in layout_type.lower()
    )

    if len(pages) == 2:
        page_label = f"Pages {pages[0]}–{pages[1]}"
        unit_class = "spread"
    else:
        page_label = f"Page {pages[0]}" if pages else "Page"
        unit_class = "single"

    blocks_html = "".join(
        render_block(
            block,
            assets,
            zine_dir,
            output_dir,
        )
        for block in page_unit.get("blocks", [])
    )

    special_layout = ""

    if layout_type in {
        "memory-index-grid",
        "closing-memory-grid",
    }:
        special_layout = render_memory_grid(layout)

    section = page_unit.get("section", "")

    return f"""
    <article class="page-unit {unit_class}">
        <header class="page-header">
            <div>
                <span class="page-number">{escape(page_label)}</span>
                <span class="section-name">{escape(section)}</span>
            </div>
            <span class="layout-name">{escape(layout_type)}</span>
        </header>

        <div class="page-sheet">
            <div class="page-body layout-{escape(layout_slug)}">
                {special_layout}
                {blocks_html}
            </div>
        </div>
    </article>
    """



def build_html(zine_data, zine_path, output_path):
    project = zine_data.get("project", {})

    title = project.get("title", "Untitled Zine")
    description = project.get("description", "")

    assets = build_asset_index(zine_data)

    zine_dir = zine_path.parent
    output_dir = output_path.parent

    page_units = "".join(
        render_page_unit(
            page_unit,
            assets,
            zine_dir,
            output_dir,
        )
        for page_unit in zine_data.get("pages", [])
    )

    total_pages = sum(
        len(page_unit.get("pages", []))
        for page_unit in zine_data.get("pages", [])
    )

    css = """
    :root {
        font-family:
            Inter,
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            sans-serif;

        background: #ecebe6;
        color: #171717;
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        padding: 0;
    }

    .site-header {
        padding: 48px 5vw 32px;
        border-bottom: 1px solid #c9c7c0;
    }

    .eyebrow {
        margin: 0 0 12px;
        font-size: 12px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        opacity: 0.55;
    }

    h1 {
        margin: 0;
        font-size: clamp(36px, 7vw, 84px);
        line-height: 0.95;
        font-weight: 500;
    }

    .description {
        max-width: 720px;
        margin-top: 24px;
        font-size: 16px;
        line-height: 1.6;
    }

    .metadata {
        margin-top: 24px;
        display: flex;
        gap: 24px;
        flex-wrap: wrap;
        font-size: 13px;
        opacity: 0.65;
    }

.publication {
    padding: 48px 5vw 100px;
    display: grid;
    gap: 48px;
    overflow-x: auto;
}

.page-unit {
    margin: 0 auto;
}

.page-unit.single {
    width: 148mm;
}

.page-unit.spread {
    width: 296mm;
}

.page-header {
    width: 100%;
    padding: 10px 2px;
    display: flex;
    justify-content: space-between;
    gap: 16px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.page-number {
    font-weight: 700;
}

.section-name {
    margin-left: 12px;
    opacity: 0.45;
}

.layout-name {
    opacity: 0.45;
    text-align: right;
}

.page-sheet {
    position: relative;
    background: #fffef9;
    border: 1px solid #d8d5ca;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
    overflow: hidden;
}

.page-unit.single .page-sheet {
    width: 148mm;
    height: 210mm;
}

.page-unit.spread .page-sheet {
    width: 296mm;
    height: 210mm;
}

.page-unit.spread .page-sheet::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    border-left: 1px dashed rgba(0, 0, 0, 0.16);
    pointer-events: none;
    z-index: 10;
}

.page-body {
    width: 100%;
    height: 100%;
    padding: 12mm;
    overflow: hidden;
}

    .block {
        position: relative;
        margin-bottom: 28px;
    }

    .block:last-child {
        margin-bottom: 0;
    }

    .block-label {
        margin-bottom: 8px;
        font-size: 10px;
        letter-spacing: 0.14em;
        opacity: 0.35;
    }

    .asset-placeholder {
        min-height: 220px;
        border: 1px dashed #aaa79e;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 6px;
        padding: 24px;
        text-align: center;
        background:
            linear-gradient(
                135deg,
                rgba(0, 0, 0, 0.02),
                rgba(0, 0, 0, 0.06)
            );
    }

    .asset-placeholder small {
        opacity: 0.45;
    }

    .asset-type {
        font-size: 11px;
        letter-spacing: 0.15em;
        opacity: 0.45;
    }

    .asset img {
        width: 100%;
        height: auto;
        display: block;
    }

    .asset figcaption {
        margin-top: 8px;
        font-size: 12px;
        opacity: 0.55;
    }

    .gallery {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
    }

    .gallery .asset-placeholder {
        min-height: 180px;
    }

    .text-content,
    .essay {
        max-width: 680px;
        font-family: Georgia, "Times New Roman", serif;
        line-height: 1.75;
        font-size: 17px;
    }

    blockquote {
        margin: 50px auto;
        max-width: 760px;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(28px, 4vw, 52px);
        line-height: 1.15;
    }

    .question {
        margin: 80px auto;
        max-width: 760px;
        font-family: Georgia, "Times New Roman", serif;
        font-size: clamp(32px, 5vw, 64px);
        line-height: 1.1;
    }

    .checklist {
        padding: 0;
        list-style: none;
        max-width: 680px;
    }

    .checklist-item {
        display: flex;
        gap: 14px;
        padding: 14px 0;
        border-bottom: 1px solid #ddd9ce;
    }

    .checkmark {
        width: 24px;
        flex: 0 0 24px;
    }

    .caption,
    .technical-note,
    .memory-note {
        margin-top: 10px;
        font-size: 12px;
        opacity: 0.55;
    }

    .memory-grid {
        display: grid;
        gap: 10px;
        max-width: 520px;
        margin: 40px auto;
    }

    .memory-cell {
        aspect-ratio: 1;
        border: 1px solid #252525;
    }

    .memory-cell.filled {
        background: #252525;
    }

    .memory-cell.empty {
        background: transparent;
    }

    .unknown-block {
        padding: 20px;
        border: 1px dashed #999;
    }

    .footer {
        padding: 32px 5vw;
        border-top: 1px solid #c9c7c0;
        font-size: 12px;
        opacity: 0.55;
    }
/* --------------------------------------------------
   Layout-aware Renderer v0.3
   -------------------------------------------------- */


/* Full-page photography */

.layout-full-page,
.layout-full-bleed-spread {
    padding: 0;
}

.layout-full-page > .block-photo,
.layout-full-bleed-spread > .block-photo {
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-full-page .asset,
.layout-full-bleed-spread .asset {
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-full-page .asset img,
.layout-full-bleed-spread .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-full-page .asset-placeholder,
.layout-full-bleed-spread .asset-placeholder {
    width: 100%;
    height: 100%;
    min-height: 0;
    border: 0;
}

.layout-full-page .block-label,
.layout-full-bleed-spread .block-label {
    position: absolute;
    top: 4mm;
    left: 4mm;
    z-index: 20;
}


/* Image + offset text */

.layout-image-text-offset {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 8mm;
}

.layout-image-text-offset > .block-photo {
    grid-column: 2;
    grid-row: 1;
    margin: 0;
}

.layout-image-text-offset > .block-text {
    grid-column: 1;
    grid-row: 2;
    margin: 0;
}

.layout-image-text-offset .asset-placeholder {
    height: 100%;
    min-height: 0;
}


/* Recipe page */

.layout-recipe-page {
    display: grid;
    grid-template-columns: 1.25fr 0.75fr;
    gap: 8mm;
    align-items: stretch;
}

.layout-recipe-page > .block-text {
    grid-column: 1;
    align-self: start;
}

.layout-recipe-page > .block-photo {
    grid-column: 2;
    align-self: end;
}

.layout-recipe-page .asset-placeholder {
    min-height: 95mm;
}


/* Photo + location */

.layout-photo-with-location-note {
    display: grid;
    grid-template-rows: 1fr auto;
    gap: 7mm;
}

.layout-photo-with-location-note > .block-photo {
    min-height: 0;
    margin: 0;
}

.layout-photo-with-location-note .asset-placeholder {
    height: 100%;
}


/* Photo + reflection */

.layout-image-with-reflection,
.layout-image-with-short-text {
    display: grid;
    grid-template-rows: 2fr 1fr;
    gap: 7mm;
}

.layout-image-with-reflection > .block-photo,
.layout-image-with-short-text > .block-photo {
    min-height: 0;
    margin: 0;
}

.layout-image-with-reflection .asset-placeholder,
.layout-image-with-short-text .asset-placeholder {
    height: 100%;
}


/* One checklist across a spread */

.layout-spread-checklist {
    padding-left: 16mm;
    padding-right: 16mm;
}

.layout-spread-checklist > .block-checklist {
    width: 100%;
}

.layout-spread-checklist .block-title {
    margin: 5mm 0 10mm;
    text-align: center;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 28px;
    font-weight: 400;
}

.layout-spread-checklist .checklist {
    max-width: none;
    column-count: 2;
    column-gap: 28mm;
}

.layout-spread-checklist .checklist-item {
    break-inside: avoid;
    margin-bottom: 3mm;
}


/* Question page */

.layout-question-page {
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
}

.layout-question-page .block-question {
    margin-top: 25mm;
}

.layout-question-page .question {
    margin: 0;
    text-align: center;
}

.layout-question-page::after {
    content: "";
    display: block;
    width: 82%;
    height: 55mm;
    margin: 16mm auto 0;

    background:
        repeating-linear-gradient(
            to bottom,
            transparent 0,
            transparent 12mm,
            rgba(0, 0, 0, 0.28) 12mm,
            rgba(0, 0, 0, 0.28) calc(12mm + 1px)
        );
}


/* Memory Index */

.layout-memory-index-grid {
    display: flex;
    flex-direction: column;
}

.layout-memory-index-grid > .block-text:first-of-type {
    order: 1;
}

.layout-memory-index-grid > .memory-grid {
    order: 2;
}

.layout-memory-index-grid > .block-text:last-of-type {
    order: 3;
}

.layout-memory-index-grid > .memory-note {
    order: 4;
}


/* Closing memory grid */

.layout-closing-memory-grid {
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.layout-closing-memory-grid > .memory-grid {
    margin-top: 0;
}


/* Stronger center fold */

.page-unit.spread .page-sheet::after {
    border-left: 1px dashed rgba(0, 0, 0, 0.30);
    z-index: 999;
}
@media (max-width: 700px) {
    .site-header,
    .publication {
        padding-left: 20px;
        padding-right: 20px;
    }

    .page-body {
        padding: 20px;
    }

    .layout-full-page,
    .layout-full-bleed-spread {
        padding: 0;
    }

    .gallery {
        grid-template-columns: 1fr;
    }
}
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>{escape(title)} — ZineOS Preview</title>

    <style>
{css}
    </style>
</head>

<body>

<header class="site-header">
    <p class="eyebrow">ZineOS Editorial Preview</p>

    <h1>{escape(title)}</h1>

    <p class="description">
        {escape(description)}
    </p>

    <div class="metadata">
        <span>ZineOS {escape(zine_data.get("zineos_version", ""))}</span>
        <span>{total_pages} pages</span>
        <span>{escape(project.get("status", ""))}</span>
    </div>
</header>

<main class="publication">
    {page_units}
</main>

<footer class="footer">
    Generated by ZineOS Preview Renderer v0.3
</footer>

</body>
</html>
"""


def main():
    if len(sys.argv) > 3:
        print(
            "Usage: python scripts/build_preview.py "
            "[zine.yaml] [output.html]"
        )
        return 2

    zine_path = (
        Path(sys.argv[1])
        if len(sys.argv) >= 2
        else DEFAULT_ZINE_PATH
    )

    output_path = (
        Path(sys.argv[2])
        if len(sys.argv) == 3
        else DEFAULT_OUTPUT_PATH
    )

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

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    generated_html = build_html(
        zine_data,
        zine_path,
        output_path,
    )

    output_path.write_text(
        generated_html,
        encoding="utf-8",
    )

    try:
        display_path = output_path.relative_to(ROOT)
    except ValueError:
        display_path = output_path

    print(f"PREVIEW ✓ {display_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

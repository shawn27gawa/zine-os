#!/usr/bin/env python3

import html
import os
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"
DEFAULT_OUTPUT_PATH = ROOT / "preview" / "ZINE_001.html"


def default_preview_output(zine_data):
    project_id = zine_data.get("project", {}).get("id", "publication")
    stem = re.sub(r"[^A-Za-z0-9]+", "_", str(project_id)).strip("_").upper()
    return ROOT / "preview" / f"{stem or 'PUBLICATION'}.html"


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

    source_path = (zine_dir / source).resolve()

    if not source_path.exists():
        return asset, None

    relative_path = os.path.relpath(
        source_path,
        output_dir.resolve(),
    )

    return asset, relative_path


def placement_attributes(placement):
    if not isinstance(placement, dict):
        return ""
    desktop = placement.get("desktop", {})
    mobile = placement.get("mobile", desktop)

    def mode_values(settings, prefix):
        fit = settings.get("fit", "cover")
        x = settings.get("x", 50)
        y = settings.get("y", 50)
        scale = settings.get("scale", 1)
        return (
            f"--studio-{prefix}fit: {escape(str(fit))}; "
            f"--studio-{prefix}position: {escape(str(x))}% {escape(str(y))}%; "
            f"--studio-{prefix}scale: {escape(str(scale))};"
        )

    style = f"{mode_values(desktop, '')} {mode_values(mobile, 'mobile-')}"
    return f' data-studio-placement style="{style}"'


def text_placement_attributes(placement):
    if not isinstance(placement, dict):
        return ""
    variables = {
        "font_size_px": ("font-size", "px"),
        "line_height": ("line-height", ""),
        "width_percent": ("width", "%"),
        "x_mm": ("x", "mm"),
        "y_mm": ("y", "mm"),
        "columns": ("columns", ""),
        "rule_spacing_mm": ("rule-spacing", "mm"),
    }
    values = []
    for field, (name, unit) in variables.items():
        value = placement.get(field)
        if value is not None:
            values.append(f"--studio-text-{name}: {escape(str(value))}{unit};")
    return f' data-studio-text-placement style="{" ".join(values)}"' if values else ""


def field_text_placement(studio, field):
    placements = studio.get("text_placements", {})
    if field in placements:
        return placements[field]
    if field == "content":
        return studio.get("text_placement")
    return None


def render_asset_visual(
    asset_id, assets, zine_dir, output_dir, label="IMAGE", placement=None
):
    asset, relative_path = resolve_asset_path(
        asset_id,
        assets,
        zine_dir,
        output_dir,
    )

    title = asset.get("title", asset_id) if asset else asset_id

    if relative_path:
        return f"""
        <figure class="asset"{placement_attributes(placement)}>
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


def render_memory_grid(layout, assets, zine_dir, output_dir):
    settings = layout.get("settings", {})

    rows = int(settings.get("rows", 4))
    columns = int(settings.get("columns", 5))

    filled_cells = set(settings.get("filled_cells", []))
    image_assets = settings.get("assets", [])
    asset_placements = settings.get("asset_placements", {})

    cells = []

    for index in range(1, rows * columns + 1):
        asset_id = image_assets[index - 1] if index <= len(image_assets) else None
        asset, relative_path = resolve_asset_path(
            asset_id,
            assets,
            zine_dir,
            output_dir,
        ) if asset_id else (None, None)
        state = "filled" if relative_path or index in filled_cells else "empty"
        image_html = ""

        if relative_path:
            title = asset.get("title", asset_id)
            placement = asset_placements.get(asset_id)
            image = (
                f'<img src="{escape(relative_path)}" '
                f'alt="{escape(title)}">'
            )
            image_html = (
                f'<span class="memory-image"'
                f'{placement_attributes(placement)}>{image}</span>'
                if placement
                else image
            )

        cells.append(
            f'<div class="memory-cell {state}" '
            f'title="Memory cell {index}">{image_html}</div>'
        )

    meaning = settings.get(
        "empty_cells_meaning",
        settings.get("relationship_to_opening", ""),
    )

    note_html = (
        f'<div class="memory-note">{escape(meaning)}</div>'
        if meaning
        else ""
    )

    return f"""
    <div
        class="memory-grid"
        style="grid-template-columns: repeat({columns}, 1fr); grid-template-rows: repeat({rows}, 1fr);"
    >
        {''.join(cells)}
    </div>
    {note_html}
    """


def render_checklist(block, studio):
    items = []

    for item_index, item in enumerate(block.get("items", [])):
        checked = bool(item.get("checked", False))
        mark = "✓" if checked else "○"

        items.append(
            f"""
            <li class="checklist-item">
                <span class="checkmark">{mark}</span>
                <span{ text_placement_attributes(field_text_placement(studio, f"items[{item_index}].text")) }>{escape(item.get("text", ""))}</span>
            </li>
            """
        )

    title = block.get("title")

    title_html = (
        f'<h4 class="block-title"{text_placement_attributes(field_text_placement(studio, "title"))}>{escape(title)}</h4>'
        if title
        else ""
    )

    return f"""
    {title_html}
    <ul class="checklist">
        {''.join(items)}
    </ul>
    """


def render_gallery(block, assets, zine_dir, output_dir, placements=None):
    rendered_assets = []
    placements = placements or {}

    for asset_id in block.get("assets", []):
        rendered_assets.append(
            render_asset_visual(
                asset_id,
                assets,
                zine_dir,
                output_dir,
                label="PHOTO",
                placement=placements.get(asset_id),
            )
        )

    return f"""
    <div class="gallery">
        {''.join(rendered_assets)}
    </div>
    """


def render_block(block, assets, zine_dir, output_dir):
    block_type = block.get("type", "UNKNOWN")
    studio = block.get("metadata", {}).get("zineos_studio", {})
    asset_placements = studio.get("asset_placements", {})

    content = ""

    if block_type == "PHOTO":
        content = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="PHOTO",
            placement=asset_placements.get(block.get("asset")),
        )

    elif block_type == "MAP":
        content = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="MAP",
            placement=asset_placements.get(block.get("asset")),
        )

    elif block_type == "GALLERY":
        content = render_gallery(
            block,
            assets,
            zine_dir,
            output_dir,
            placements=asset_placements,
        )

    elif block_type == "CLOSEUP":
        asset_html = render_asset_visual(
            block.get("asset"),
            assets,
            zine_dir,
            output_dir,
            label="CLOSEUP",
            placement=asset_placements.get(block.get("asset")),
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
        content = render_checklist(block, studio)

    elif block_type == "QUESTION":
        content = f"""
        <div class="question"{text_placement_attributes(field_text_placement(studio, "content"))}>
            {escape(block.get("content", ""))}
        </div>
        """

    elif block_type == "QUOTE":
        content = f"""
        <blockquote{text_placement_attributes(field_text_placement(studio, "content"))}>
            {escape(block.get("content", ""))}
        </blockquote>
        """

    elif block_type in {"TEXT", "CAPTION"}:
        text = block.get("content", block.get("caption", ""))

        content = f"""
        <div class="text-content"{text_placement_attributes(field_text_placement(studio, "content"))}>
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
        f'<div class="caption"{text_placement_attributes(field_text_placement(studio, "caption"))}>{escape(caption)}</div>'
        if caption
        else ""
    )

    text_attributes = (
        text_placement_attributes(studio.get("text_placement"))
        if not studio.get("text_placements")
        else ""
    )

    return f"""
    <section class="block block-{escape(block_type.lower())}"{text_attributes}>
        <div class="block-label">{escape(block_type)}</div>
        {content}
        {caption_html}
    </section>
    """

def render_page_unit(page_unit, assets, zine_dir, output_dir):
    pages = page_unit.get("pages", [])
    layout = page_unit.get("layout", {})
    layout_settings = layout.get("settings", {})

    layout_type = layout.get("type", "unspecified")

    layout_slug = "".join(
        character
        if character.isalnum() or character == "-"
        else "-"
        for character in layout_type.lower()
    )

    layout_variant = layout.get("variant", "")
    variant_slug = "".join(
        character
        if character.isalnum() or character == "-"
        else "-"
        for character in layout_variant.lower()
    )
    variant_class = f" variant-{variant_slug}" if variant_slug else ""

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
        special_layout = render_memory_grid(
            layout,
            assets,
            zine_dir,
            output_dir,
        )

    section = page_unit.get("section", "")

    image_position = layout_settings.get("image_position")
    image_position_style = (
        f' style="--image-position: {escape(image_position.strip())};"'
        if isinstance(image_position, str) and image_position.strip()
        else ""
    )

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
            <div class="page-body layout-{escape(layout_slug)}{escape(variant_class)}"{image_position_style}>
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

    .asset {
        margin: 0;
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
    object-position: var(--image-position, center center);
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
    display: none;
}

.layout-full-page figcaption,
.layout-full-bleed-spread figcaption {
    display: none;
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


/* Editorial route map spread */

.layout-trace-map-spread {
    position: relative;
    isolation: isolate;
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    grid-template-rows: repeat(10, 1fr);
    gap: 0;
    padding: 12mm;
    background: #f7f7f5;
}

.layout-trace-map-spread > .block-map {
    position: absolute;
    inset: 0;
    z-index: -1;
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-trace-map-spread > .block-map .block-label,
.layout-trace-map-spread > .block-map figcaption,
.layout-trace-map-spread > .block-photo .block-label,
.layout-trace-map-spread > .block-caption .block-label {
    display: none;
}

.layout-trace-map-spread > .block-map .asset,
.layout-trace-map-spread > .block-map img {
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-trace-map-spread > .block-map img {
    display: block;
    object-fit: cover;
}

.layout-trace-map-spread > .block-photo {
    grid-column: 1 / span 5;
    grid-row: 4 / span 5;
    z-index: 2;
    min-width: 0;
    min-height: 0;
    margin: 0;
}

.layout-trace-map-spread > .block-photo .asset,
.layout-trace-map-spread > .block-photo .asset-placeholder {
    width: 100%;
    height: 100%;
    min-height: 0;
    margin: 0;
    overflow: hidden;
    border-radius: 3mm;
    border: 1px solid rgba(93, 98, 101, 0.09);
    background: rgba(255, 255, 253, 0.88);
    box-shadow: 0 2mm 8mm rgba(39, 43, 45, 0.05);
}

.layout-trace-map-spread > .block-photo .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-trace-map-spread > .block-photo .asset-placeholder {
    color: #6f7477;
    backdrop-filter: blur(4px);
}

.layout-trace-map-spread > .block-caption {
    grid-column: 9 / span 4;
    grid-row: 7 / span 2;
    z-index: 2;
    align-self: center;
    margin: 0;
    padding: 5mm 6mm;
    border: 1px solid rgba(93, 98, 101, 0.08);
    border-radius: 3mm;
    background: rgba(255, 255, 253, 0.78);
    box-shadow: 0 1mm 5mm rgba(39, 43, 45, 0.04);
    backdrop-filter: blur(5px);
}

.layout-trace-map-spread > .block-caption .text-content {
    color: #4f5559;
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    font-size: 10px;
    font-weight: 400;
    line-height: 1.7;
    letter-spacing: 0.08em;
}

.layout-trace-map-spread > .block-text {
    grid-column: 7 / span 6;
    grid-row: 1 / span 5;
    z-index: 2;
    align-self: start;
    margin: 0;
    padding: 5mm 6mm;
    border: 1px solid rgba(93, 98, 101, 0.08);
    border-radius: 3mm;
    background: rgba(255, 255, 253, 0.84);
    box-shadow: 0 1mm 5mm rgba(39, 43, 45, 0.04);
    backdrop-filter: blur(5px);
}

.layout-trace-map-spread > .block-text .block-label {
    display: none;
}

.layout-trace-map-spread > .block-text .text-content {
    color: #3f4548;
    font-size: 10px;
    line-height: 1.62;
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

.layout-question-page > .block-text {
    width: 100%;
    margin: 0;
}

.layout-question-page > .block-text .block-label {
    display: none;
}

.layout-question-page > .block-text .text-content {
    font-size: 14px;
    line-height: 1.9;
}

.layout-question-page .block-question {
    margin-top: 18mm;
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
        linear-gradient(rgba(0, 0, 0, 0.24), rgba(0, 0, 0, 0.24)) 0 0 / 100% 1px no-repeat,
        linear-gradient(rgba(0, 0, 0, 0.24), rgba(0, 0, 0, 0.24)) 0 33.333% / 100% 1px no-repeat,
        linear-gradient(rgba(0, 0, 0, 0.24), rgba(0, 0, 0, 0.24)) 0 66.666% / 100% 1px no-repeat,
        linear-gradient(rgba(0, 0, 0, 0.24), rgba(0, 0, 0, 0.24)) 0 100% / 100% 1px no-repeat;
}


/* Memory Index */

.layout-memory-index-grid,
.layout-closing-memory-grid {
    position: relative;
    padding: 0;
    overflow: hidden;
}

.layout-memory-index-grid .memory-grid,
.layout-closing-memory-grid .memory-grid {
    width: 100%;
    height: 100%;
    max-width: none;
    margin: 0;
    gap: 0;
}

.layout-memory-index-grid .memory-cell,
.layout-closing-memory-grid .memory-cell {
    min-width: 0;
    min-height: 0;
    aspect-ratio: auto;
    overflow: hidden;
    border: 0;
}

.layout-memory-index-grid .memory-cell img,
.layout-closing-memory-grid .memory-cell img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: cover;
    filter: grayscale(1);
}

.layout-memory-index-grid::after {
    content: "";
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 2;
    height: 26%;
    background: #f7f6f1;
}

.layout-memory-index-grid .memory-grid {
    position: absolute;
    inset: 0 0 26%;
    z-index: 1;
    height: auto;
}

.layout-memory-index-grid > .block-text {
    position: absolute;
    right: 0;
    left: 0;
    z-index: 3;
    margin: 0;
    padding-right: 6mm;
    padding-left: 6mm;
    color: #0a0a0a;
    background: transparent;
}

.layout-memory-index-grid > .block-text .block-label,
.layout-closing-memory-grid > .block-text {
    display: none;
}

.layout-memory-index-grid > .block-text:nth-of-type(1) {
    bottom: 17.5%;
    height: 8.5%;
    padding-top: 4mm;
}

.layout-memory-index-grid > .block-text:nth-of-type(1) .text-content {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 3.4mm;
    line-height: 1;
    letter-spacing: 0.06em;
}

.layout-memory-index-grid > .block-text:nth-of-type(2) {
    bottom: 0;
    display: flex;
    align-items: center;
    height: 17.5%;
    padding-bottom: 2mm;
}

.layout-memory-index-grid > .block-text:nth-of-type(2) .text-content {
    white-space: nowrap;
    font-family: "Arial Black", Arial, Helvetica, sans-serif;
    font-size: 16.5mm;
    font-weight: 900;
    line-height: 0.88;
    letter-spacing: -0.07em;
}


/* Full-spread editorial gallery */

.layout-asymmetric-gallery {
    position: relative;
    padding: 0;
}

.layout-asymmetric-gallery > .block-gallery,
.layout-asymmetric-gallery .gallery {
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-asymmetric-gallery .gallery {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: repeat(2, 1fr);
    gap: 1.5mm;
}

.layout-asymmetric-gallery .asset {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}

.layout-asymmetric-gallery .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-asymmetric-gallery .block-label,
.layout-asymmetric-gallery figcaption,
.layout-asymmetric-gallery .caption {
    display: none;
}

.layout-asymmetric-gallery > .block-text {
    position: absolute;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 5;
    margin: 0;
    padding: 5mm 10mm;
    background: rgba(247, 246, 241, 0.90);
    backdrop-filter: blur(4px);
}

.layout-asymmetric-gallery > .block-text .block-label {
    display: none;
}

.layout-asymmetric-gallery > .block-text .text-content {
    column-count: 2;
    column-gap: 18mm;
    font-size: 10.5px;
    line-height: 1.58;
}


/* Reusable photo-led rhythm for quiet, energetic, and paired spreads */

.layout-photo-rhythm-spread {
    position: relative;
    padding: 0;
    background: #f3f1eb;
}

.layout-photo-rhythm-spread > .block-gallery,
.layout-photo-rhythm-spread .gallery {
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-photo-rhythm-spread .gallery {
    gap: 1.5mm;
}

.layout-photo-rhythm-spread .asset {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}

.layout-photo-rhythm-spread .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-photo-rhythm-spread .block-label,
.layout-photo-rhythm-spread figcaption,
.layout-photo-rhythm-spread .caption {
    display: none;
}

.layout-photo-rhythm-spread > .block-text {
    position: absolute;
    z-index: 3;
    margin: 0;
}

.layout-photo-rhythm-spread > .block-text .text-content {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9px;
    font-weight: 600;
    line-height: 1;
    letter-spacing: 0.18em;
}

.layout-photo-rhythm-spread.variant-breath-left .gallery,
.layout-photo-rhythm-spread.variant-breath-right .gallery {
    display: grid;
    grid-template-columns: 44% 56%;
    gap: 0;
}

.layout-photo-rhythm-spread.variant-breath-left .asset {
    grid-column: 1;
}

.layout-photo-rhythm-spread.variant-breath-right .asset {
    grid-column: 2;
}

.layout-photo-rhythm-spread.variant-breath-left > .block-text {
    right: 12mm;
    bottom: 12mm;
    text-align: right;
}

.layout-photo-rhythm-spread.variant-breath-right > .block-text {
    left: 12mm;
    bottom: 12mm;
}

.layout-photo-rhythm-spread.variant-diptych .gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: 1fr;
}

.layout-photo-rhythm-spread.variant-diptych > .block-text {
    right: 8mm;
    bottom: 8mm;
    padding: 3mm 4mm;
    background: rgba(247, 246, 241, 0.88);
    backdrop-filter: blur(4px);
}

.layout-photo-rhythm-spread.variant-grid .gallery {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
}


/* Edge-led image and text pages */

.layout-image-with-reflection,
.layout-image-with-short-text {
    padding: 0;
    gap: 0;
}

.layout-image-with-reflection {
    grid-template-rows: minmax(0, 1fr) auto;
}

.layout-image-with-short-text {
    grid-template-rows: minmax(0, 1fr) auto;
}

.layout-image-with-reflection .asset,
.layout-image-with-short-text .asset {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

.layout-image-with-reflection .asset img,
.layout-image-with-short-text .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-image-with-reflection > .block-text,
.layout-image-with-short-text > .block-text {
    margin: 0;
    padding: 7mm 9mm;
}

.layout-image-with-reflection > .block-text .block-label,
.layout-image-with-short-text > .block-text .block-label {
    display: none;
}

.layout-image-with-reflection > .block-text .text-content {
    column-count: 2;
    column-gap: 8mm;
    font-size: 10.5px;
    line-height: 1.55;
}

.layout-image-with-short-text > .block-text {
    padding: 5mm 8mm;
}

.layout-image-with-short-text > .block-text .text-content {
    font-size: 10.5px;
    line-height: 1.5;
}

.layout-image-with-reflection .block-photo .block-label,
.layout-image-with-reflection .block-photo figcaption,
.layout-image-with-short-text .block-photo .block-label,
.layout-image-with-short-text .block-photo figcaption {
    display: none;
}


/* Larger upper-right image with protected copy area */

.layout-image-text-offset {
    grid-template-columns: 0.5fr 1.5fr;
    grid-template-rows: 1.45fr 0.55fr;
    gap: 6mm;
    padding: 6mm;
}

.layout-image-text-offset .asset,
.layout-image-text-offset .asset img {
    width: 100%;
    height: 100%;
}

.layout-image-text-offset .asset img {
    object-fit: cover;
}

.layout-image-text-offset .block-photo .block-label,
.layout-image-text-offset .block-photo figcaption {
    display: none;
}

.layout-image-text-offset > .block-text {
    grid-column: 1 / span 2;
    grid-row: 2;
    align-self: start;
    width: 94mm;
    max-width: 100%;
    margin: 0;
}

.layout-image-text-offset > .block-text .block-label {
    display: none;
}

.layout-image-text-offset > .block-text .text-content {
    font-size: 11.5px;
    line-height: 1.62;
}


/* Full-image stories with restrained editorial cards */

.layout-full-page-story,
.layout-full-bleed-story-spread {
    position: relative;
    padding: 0;
}

.layout-full-page-story > .block-photo,
.layout-full-bleed-story-spread > .block-photo {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    margin: 0;
}

.layout-full-page-story .asset,
.layout-full-page-story .asset img,
.layout-full-bleed-story-spread .asset,
.layout-full-bleed-story-spread .asset img {
    width: 100%;
    height: 100%;
}

.layout-full-page-story .asset img,
.layout-full-bleed-story-spread .asset img {
    object-fit: cover;
}

.layout-full-page-story .block-photo .block-label,
.layout-full-page-story .block-photo figcaption,
.layout-full-bleed-story-spread .block-photo .block-label,
.layout-full-bleed-story-spread .block-photo figcaption {
    display: none;
}

.layout-full-page-story > .block-text,
.layout-full-bleed-story-spread > .block-text {
    position: absolute;
    z-index: 3;
    margin: 0;
    border: 1px solid rgba(35, 35, 32, 0.08);
    background: rgba(247, 246, 241, 0.88);
    backdrop-filter: blur(5px);
}

.layout-full-page-story > .block-text {
    top: 8mm;
    left: 8mm;
    width: 64mm;
    padding: 5mm;
}

.layout-full-bleed-story-spread > .block-text {
    top: 8mm;
    left: 8mm;
    width: 78mm;
    padding: 5mm 6mm;
}

.layout-full-page-story > .block-text .block-label,
.layout-full-bleed-story-spread > .block-text .block-label {
    display: none;
}

.layout-full-page-story > .block-text .text-content {
    font-size: 9.5px;
    line-height: 1.5;
}

.layout-full-bleed-story-spread > .block-text .text-content {
    font-size: 10.5px;
    line-height: 1.58;
}


/* Text-led memory pages */

.layout-reflective-notes > .block-text,
.layout-text-page > .block-text {
    margin: 0;
}

.layout-reflective-notes {
    position: relative;
    padding: 14mm 12mm;
    background:
        repeating-linear-gradient(
            to bottom,
            transparent 0,
            transparent 15.8mm,
            rgba(30, 30, 28, 0.07) 15.8mm,
            rgba(30, 30, 28, 0.07) calc(15.8mm + 1px)
        ),
        #f5f3ed;
}

.layout-reflective-notes > .block-text .block-label,
.layout-text-page > .block-text .block-label {
    display: none;
}

.layout-reflective-notes > .block-text .text-content {
    font-size: 15px;
    line-height: 1.9;
}

.layout-text-page {
    position: relative;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-content: center;
    gap: 10mm;
    padding: 12mm;
    background: #f3f1eb;
}

.layout-text-page::after {
    content: "";
    position: absolute;
    top: 12mm;
    bottom: 12mm;
    left: 50%;
    border-left: 1px solid rgba(30, 30, 28, 0.09);
}

.layout-text-page > .block-text .text-content {
    font-size: 10.5px;
    line-height: 1.55;
}


/* P8 bottle and paired glasses */

.layout-recipe-page {
    position: relative;
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    grid-template-rows: repeat(12, 1fr);
    gap: 0;
    padding: 8mm;
}

.layout-recipe-page > .block-text {
    grid-column: 1 / span 6;
    grid-row: 2 / span 10;
    z-index: 2;
    margin: 0;
}

.layout-recipe-page > .block-photo:first-child {
    grid-column: 7 / span 5;
    grid-row: 1 / span 8;
    z-index: 1;
    margin: 0;
    align-self: stretch;
}

.layout-recipe-page > .block-photo:last-child {
    grid-column: 6 / span 7;
    grid-row: 8 / span 5;
    z-index: 3;
    margin: 0;
    align-self: stretch;
}

.layout-recipe-page .asset,
.layout-recipe-page .asset img {
    width: 100%;
    height: 100%;
}

.layout-recipe-page .asset img {
    object-fit: contain;
}

.layout-recipe-page .block-photo .block-label,
.layout-recipe-page .block-photo figcaption,
.layout-recipe-page .block-photo .caption {
    display: none;
}


/* P18–19: people-led editorial collage */

.layout-editorial-collage {
    position: relative;
    display: block;
    padding: 0;
}

.layout-editorial-collage > .block-gallery,
.layout-editorial-collage .gallery {
    min-height: 0;
    margin: 0;
}

.layout-editorial-collage > .block-gallery {
    height: 100%;
}

.layout-editorial-collage .gallery {
    width: 100%;
    height: 100%;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 0;
}

.layout-editorial-collage .asset {
    min-width: 0;
    min-height: 0;
    overflow: hidden;
}

.layout-editorial-collage .asset:nth-child(3) { grid-column: 1; grid-row: 1; }
.layout-editorial-collage .asset:nth-child(4) { grid-column: 1; grid-row: 2; }
.layout-editorial-collage .asset:nth-child(1) { grid-column: 2; grid-row: 1; }
.layout-editorial-collage .asset:nth-child(2) { grid-column: 2; grid-row: 2; }

.layout-editorial-collage .asset img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.layout-editorial-collage .asset:nth-child(3) img { object-position: center 48%; }
.layout-editorial-collage .asset:nth-child(4) img { object-position: center 24%; }
.layout-editorial-collage .asset:nth-child(1) img { object-position: center 45%; }
.layout-editorial-collage .asset:nth-child(2) img { object-position: center 52%; }

.layout-editorial-collage > .block-text {
    position: absolute;
    left: 0;
    bottom: 0;
    z-index: 2;
    width: 50%;
    margin: 0;
    padding: 5mm 8mm;
    background: rgba(248, 247, 242, 0.94);
}

.layout-editorial-collage > .block-text .block-label {
    display: none;
}

.layout-editorial-collage > .block-text .text-content {
    font-size: 11px;
    line-height: 1.6;
}

.layout-editorial-collage .block-gallery .block-label,
.layout-editorial-collage .block-gallery figcaption,
.layout-editorial-collage .block-gallery .caption {
    display: none;
}


/* P2–3: quiet opening breath inside the heavier cover */

.layout-opening-breath-spread {
    position: relative;
    padding: 0;
    overflow: hidden;
    background: #e9e5dc;
}

.layout-opening-breath-spread::after {
    content: "";
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    border-left: 1px solid rgba(25, 25, 23, 0.08);
}

.layout-opening-breath-spread > .block-text {
    position: absolute;
    bottom: 12mm;
    z-index: 1;
    margin: 0;
}

.layout-opening-breath-spread > .block-text:first-child {
    left: 12mm;
}

.layout-opening-breath-spread > .block-text:nth-child(2) {
    right: 12mm;
    bottom: 20mm;
    text-align: right;
}

.layout-opening-breath-spread > .block-text:last-child {
    right: 12mm;
    width: 120mm;
    text-align: right;
}

.layout-opening-breath-spread .block-label {
    display: none;
}

.layout-opening-breath-spread .text-content {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 10px;
    font-weight: 600;
    line-height: 1;
    letter-spacing: 0.16em;
}

.layout-opening-breath-spread > .block-text:last-child .text-content {
    font-size: 7px;
    font-weight: 400;
    line-height: 1.4;
    letter-spacing: 0.1em;
}


/* Creator-approved text placement adjustments */

.layout-trace-map-spread > .block-caption .text-content,
.layout-trace-map-spread > .block-text .text-content {
    font-size: 12.75px;
}

.layout-reflective-notes > .block-text {
    width: 84%;
    transform: translateY(6.5mm);
}

.layout-reflective-notes > .block-text .text-content {
    line-height: 2.5;
}

.layout-full-page-story > .block-text {
    width: 47%;
    transform: translateX(-7.5mm);
}

.layout-image-text-offset > .block-text {
    width: 64%;
}

.layout-full-bleed-story-spread > .block-text {
    width: 26%;
}

.layout-text-page > .block-text:first-child {
    transform: translateX(-3mm);
}

.layout-text-page > .block-text:last-child {
    transform: translateX(3mm);
}

.layout-recipe-page > .block-text > .block-label,
.layout-spread-checklist > .block-checklist > .block-label,
.layout-question-page > .block-question > .block-label {
    display: none;
}

.layout-spread-checklist .block-title {
    width: 89%;
    transform: translateX(11mm);
}

.layout-question-page > .block-text {
    width: 84%;
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
    .layout-full-bleed-spread,
    .layout-full-page-story,
    .layout-full-bleed-story-spread,
    .layout-memory-index-grid,
    .layout-opening-breath-spread,
    .layout-closing-memory-grid,
    .layout-asymmetric-gallery,
    .layout-photo-rhythm-spread,
    .layout-image-with-reflection,
    .layout-image-with-short-text,
    .layout-editorial-collage {
        padding: 0;
    }

    .gallery {
        grid-template-columns: 1fr;
    }
}
    """

    if "data-studio-" in page_units:
        css += """

/* ZineOS Studio applied placement controls */

[data-studio-placement] {
    overflow: hidden;
}

[data-studio-placement] img {
    object-fit: var(--studio-fit) !important;
    object-position: var(--studio-position) !important;
    transform: scale(var(--studio-scale)) !important;
    transform-origin: var(--studio-position) !important;
}

.memory-image {
    display: block;
    width: 100%;
    height: 100%;
    overflow: hidden;
}

[data-studio-text-placement] {
    width: var(--studio-text-width, auto) !important;
    transform: translate(
        var(--studio-text-x, 0),
        var(--studio-text-y, 0)
    ) !important;
}

[data-studio-text-placement] {
    font-size: var(--studio-text-font-size, inherit) !important;
    line-height: var(--studio-text-line-height, inherit) !important;
    column-count: var(--studio-text-columns, 1);
}

@media (max-width: 760px) {
    [data-studio-placement] img {
        object-fit: var(--studio-mobile-fit, var(--studio-fit)) !important;
        object-position: var(
            --studio-mobile-position,
            var(--studio-position)
        ) !important;
        transform: scale(
            var(--studio-mobile-scale, var(--studio-scale))
        ) !important;
        transform-origin: var(
            --studio-mobile-position,
            var(--studio-position)
        ) !important;
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

    if not zine_path.is_absolute():
        zine_path = ROOT / zine_path

    if not zine_path.exists():
        print(f"ERROR: Zine file not found: {zine_path}")
        return 2

    try:
        zine_data = load_yaml(zine_path)

    except yaml.YAMLError as error:
        print(f"ERROR: Unable to parse YAML: {error}")
        return 2

    if len(sys.argv) == 3:
        output_path = Path(sys.argv[2])
    elif len(sys.argv) == 1:
        output_path = DEFAULT_OUTPUT_PATH
    else:
        output_path = default_preview_output(zine_data)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

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

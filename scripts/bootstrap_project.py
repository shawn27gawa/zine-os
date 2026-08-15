#!/usr/bin/env python3

"""Create a neutral ZineOS project and a non-destructive photo-inbox review."""

import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import struct
import sys
from urllib.parse import quote

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = ROOT / "templates" / "basic" / "zine.yaml"
DEFAULT_PROJECTS_DIRECTORY = ROOT / "projects"
INVENTORY_FILENAME = "inbox.inventory.json"
REVIEW_FILENAME = "INBOX_REVIEW.html"
README_FILENAME = "README.md"
SUPPORTED_IMAGE_EXTENSIONS = {
    ".gif": "GIF",
    ".jpeg": "JPEG",
    ".jpg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}
PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class BootstrapError(ValueError):
    """A creator-correctable bootstrap input or safety error."""


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_image_format(path):
    with path.open("rb") as file:
        header = file.read(16)
    if header.startswith(b"\xff\xd8"):
        return "JPEG"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "WEBP"
    return "UNKNOWN"


def png_dimensions(path):
    with path.open("rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def gif_dimensions(path):
    with path.open("rb") as file:
        header = file.read(10)
    if len(header) < 10 or header[:6] not in {b"GIF87a", b"GIF89a"}:
        return None
    return struct.unpack("<HH", header[6:10])


def webp_dimensions(path):
    with path.open("rb") as file:
        header = file.read(30)
    if len(header) < 16 or header[:4] != b"RIFF" or header[8:12] != b"WEBP":
        return None
    kind = header[12:16]
    if kind == b"VP8X" and len(header) >= 30:
        width = 1 + int.from_bytes(header[24:27], "little")
        height = 1 + int.from_bytes(header[27:30], "little")
        return width, height
    if kind == b"VP8L" and len(header) >= 25 and header[20] == 0x2F:
        bits = int.from_bytes(header[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b"VP8 " and len(header) >= 30 and header[23:26] == b"\x9d\x01\x2a":
        width, height = struct.unpack("<HH", header[26:30])
        return width & 0x3FFF, height & 0x3FFF
    return None


def exif_orientation(payload):
    if not payload.startswith(b"Exif\x00\x00"):
        return None
    tiff = payload[6:]
    if len(tiff) < 8 or tiff[:2] not in {b"II", b"MM"}:
        return None
    byteorder = "little" if tiff[:2] == b"II" else "big"
    if int.from_bytes(tiff[2:4], byteorder) != 42:
        return None
    offset = int.from_bytes(tiff[4:8], byteorder)
    if offset + 2 > len(tiff):
        return None
    count = int.from_bytes(tiff[offset:offset + 2], byteorder)
    for index in range(count):
        start = offset + 2 + index * 12
        entry = tiff[start:start + 12]
        if len(entry) < 12:
            break
        tag = int.from_bytes(entry[:2], byteorder)
        kind = int.from_bytes(entry[2:4], byteorder)
        item_count = int.from_bytes(entry[4:8], byteorder)
        if tag == 0x0112 and kind == 3 and item_count == 1:
            return int.from_bytes(entry[8:10], byteorder)
    return None


def jpeg_metadata(path):
    dimensions = None
    orientation = None
    with path.open("rb") as file:
        if file.read(2) != b"\xff\xd8":
            return None, None
        while True:
            marker_start = file.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue
            marker = file.read(1)
            while marker == b"\xff":
                marker = file.read(1)
            if not marker or marker in {b"\xd8", b"\xd9"}:
                continue
            if marker == b"\xda":
                break
            length_data = file.read(2)
            if len(length_data) != 2:
                break
            length = int.from_bytes(length_data, "big")
            if length < 2:
                break
            payload = file.read(length - 2)
            marker_value = marker[0]
            if marker_value == 0xE1 and orientation is None:
                orientation = exif_orientation(payload)
            if marker_value in {
                0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
            } and len(payload) >= 5:
                height = int.from_bytes(payload[1:3], "big")
                width = int.from_bytes(payload[3:5], "big")
                dimensions = (width, height)
            if dimensions and orientation is not None:
                break
    return dimensions, orientation


def image_metadata(path, image_format):
    exif_value = None
    if image_format == "PNG":
        dimensions = png_dimensions(path)
    elif image_format == "GIF":
        dimensions = gif_dimensions(path)
    elif image_format == "WEBP":
        dimensions = webp_dimensions(path)
    else:
        dimensions, exif_value = jpeg_metadata(path)

    if dimensions and exif_value in {5, 6, 7, 8}:
        width, height = dimensions[1], dimensions[0]
    elif dimensions:
        width, height = dimensions
    else:
        width = height = None

    if width is None:
        orientation = "unknown"
    elif width > height:
        orientation = "landscape"
    elif height > width:
        orientation = "portrait"
    else:
        orientation = "square"

    return {
        "width": width,
        "height": height,
        "orientation": orientation,
        "exifOrientation": exif_value,
    }


def inventory_inbox(inbox_path, recursive=True):
    paths = inbox_path.rglob("*") if recursive else inbox_path.glob("*")
    images = [
        path for path in paths
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(inbox_path).parts)
        and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    images.sort(key=lambda path: path.relative_to(inbox_path).as_posix().casefold())

    candidates = []
    first_by_hash = {}
    for index, path in enumerate(images, start=1):
        relative_path = path.relative_to(inbox_path).as_posix()
        expected_format = SUPPORTED_IMAGE_EXTENSIONS[path.suffix.lower()]
        image_format = detect_image_format(path)
        digest = sha256_file(path)
        metadata = image_metadata(path, image_format)
        candidate_id = f"candidate-{index:04d}"
        candidate = {
            "id": candidate_id,
            "filename": path.name,
            "relativePath": relative_path,
            "format": image_format,
            "expectedFormat": expected_format,
            "extension": path.suffix,
            "extensionMatchesFormat": image_format == expected_format,
            "bytes": path.stat().st_size,
            "sha256": digest,
            **metadata,
            "selectionStatus": "unassigned",
            "duplicateOf": first_by_hash.get(digest),
        }
        first_by_hash.setdefault(digest, candidate_id)
        candidates.append(candidate)
    return candidates


def neutralize_template(template_data, project_id, title, language, creator):
    data = dict(template_data)
    data["project"] = {
        **template_data.get("project", {}),
        "id": project_id,
        "title": title,
        "description": "",
        "language": language,
        "status": "draft",
    }
    metadata = dict(template_data.get("metadata", {}))
    metadata.update({"creator": creator, "contributors": [], "tags": []})
    data["metadata"] = metadata
    data["assets"] = []
    data["sequence"] = [
        {"id": "opening", "title": "Opening"},
        {"id": "main", "title": "Main"},
        {"id": "ending", "title": "Ending"},
    ]
    data["pages"] = [
        {
            "id": "page-001",
            "pages": [1],
            "section": "opening",
            "blocks": [{"id": "block-001", "type": "TEXT", "content": title}],
            "layout": {"type": "minimal"},
        },
        {
            "id": "spread-002-003",
            "pages": [2, 3],
            "section": "main",
            "blocks": [{"id": "block-002", "type": "TEXT", "content": ""}],
            "layout": {"type": "open"},
        },
        {
            "id": "page-004",
            "pages": [4],
            "section": "ending",
            "blocks": [{"id": "block-003", "type": "TEXT", "content": ""}],
            "layout": {"type": "minimal"},
        },
    ]
    return data


def review_image_source(candidate, inbox_path, review_path):
    source = (inbox_path / candidate["relativePath"]).resolve()
    relative = os.path.relpath(source, review_path.resolve().parent)
    return quote(Path(relative).as_posix(), safe="/.-_~")


def build_review_html(project_id, title, inbox_path, review_path, candidates):
    cards = []
    for candidate in candidates:
        dimensions = (
            f'{candidate["width"]} × {candidate["height"]}'
            if candidate["width"] is not None else "Dimensions unavailable"
        )
        duplicate = (
            f'<span class="duplicate">Duplicate of {escape(candidate["duplicateOf"])}</span>'
            if candidate["duplicateOf"] else ""
        )
        mismatch = (
            '<span class="duplicate">Filename extension does not match file data</span>'
            if not candidate["extensionMatchesFormat"] else ""
        )
        cards.append(f"""
        <article class="candidate">
            <div class="image-wrap">
                <img src="{review_image_source(candidate, inbox_path, review_path)}"
                     alt="{escape(candidate['filename'])}" loading="lazy">
            </div>
            <div class="details">
                <strong>{escape(candidate['id'])}</strong>
                <span>{escape(candidate['relativePath'])}</span>
                <span>{dimensions} · {escape(candidate['orientation'])} · {escape(candidate['format'])}</span>
                <span class="status">UNASSIGNED</span>{duplicate}{mismatch}
            </div>
        </article>
        """)

    empty = '<p class="empty">No supported images were found.</p>' if not cards else ""
    return f"""<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} — Inbox Review</title>
    <style>
        :root {{ color-scheme: light; font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif; }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; color: #171717; background: #f4f4f1; }}
        header {{ padding: 36px clamp(20px, 5vw, 72px) 24px; border-bottom: 1px solid #d9d9d3; }}
        h1 {{ margin: 0 0 8px; font-size: clamp(28px, 5vw, 52px); font-weight: 500; }}
        header p {{ max-width: 760px; margin: 0; color: #64645f; line-height: 1.55; }}
        main {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1px; padding: 1px; background: #d9d9d3; }}
        .candidate {{ min-width: 0; background: #fff; }}
        .image-wrap {{ aspect-ratio: 4 / 3; background: #ecece8; overflow: hidden; }}
        img {{ width: 100%; height: 100%; display: block; object-fit: contain; }}
        .details {{ display: grid; gap: 5px; padding: 14px; font-size: 12px; }}
        .details span {{ overflow-wrap: anywhere; color: #666; }}
        .status {{ width: max-content; padding: 3px 6px; color: #5e4a00 !important; background: #fff0ad; border-radius: 999px; font-size: 10px; letter-spacing: .08em; }}
        .duplicate {{ color: #9d321d !important; }}
        .empty {{ padding: 30px; background: #fff; }}
    </style>
</head>
<body>
    <header>
        <h1>{escape(title)}</h1>
        <p>Project {escape(project_id)} · {len(candidates)} factual inbox candidates. Nothing is selected, assigned to a page, cropped, or copied. The creator chooses what enters the publication.</p>
    </header>
    <main>{''.join(cards)}{empty}</main>
</body>
</html>
"""


def project_readme(project_id, title, inbox_path, candidate_count):
    return f"""# {title}

This project was created from the neutral ZineOS basic template.

- Project ID: `{project_id}`
- Source inbox: `{inbox_path.resolve()}`
- Inventoried images: {candidate_count}
- Selection state: creator review required

The source inbox was read but not modified. No candidate has been copied,
selected, sequenced, placed, or cropped. Review `INBOX_REVIEW.html`, then give
the selected candidate IDs and editorial direction to the Editor/Builder.

Validate the draft:

```sh
python scripts/validate_zine.py path/to/{project_id}/zine.yaml
```
"""


def bootstrap_project(args):
    if not PROJECT_ID_PATTERN.fullmatch(args.project_id):
        raise BootstrapError("project ID must use lowercase letters, numbers, hyphens, or underscores")
    if len(args.language) < 2:
        raise BootstrapError("language must contain at least two characters")

    template_path = args.template.resolve()
    inbox_path = args.inbox.resolve()
    output_path = (
        args.output if args.output is not None
        else DEFAULT_PROJECTS_DIRECTORY / args.project_id
    ).resolve()
    if not template_path.is_file():
        raise BootstrapError(f"template not found: {template_path}")
    if not inbox_path.is_dir():
        raise BootstrapError(f"inbox directory not found: {inbox_path}")
    if output_path.exists():
        raise BootstrapError(f"output already exists; refusing to overwrite: {output_path}")
    try:
        project_relative = output_path.relative_to(ROOT)
    except ValueError as error:
        raise BootstrapError("output must be inside the ZineOS projects directory") from error
    if not project_relative.parts or project_relative.parts[0] != "projects":
        raise BootstrapError("output must be inside the ZineOS projects directory")
    if output_path == inbox_path:
        raise BootstrapError("output must be separate from the photo inbox")
    try:
        output_path.relative_to(inbox_path)
    except ValueError:
        pass
    else:
        raise BootstrapError("output must not be created inside the photo inbox")

    with template_path.open("r", encoding="utf-8") as file:
        template_data = yaml.safe_load(file)
    project_data = neutralize_template(
        template_data, args.project_id, args.title, args.language, args.creator
    )
    candidates = inventory_inbox(inbox_path, recursive=not args.top_level_only)

    inventory = {
        "format": "zineos-inbox-inventory",
        "version": 1,
        "projectId": args.project_id,
        "sourceInbox": str(inbox_path),
        "recursive": not args.top_level_only,
        "selectionStatus": "creator-review-required",
        "candidateCount": len(candidates),
        "candidates": candidates,
    }

    planned = ["zine.yaml", INVENTORY_FILENAME, REVIEW_FILENAME, README_FILENAME, "assets/"]
    if args.dry_run:
        return output_path, candidates, planned

    output_path.mkdir(parents=True)
    (output_path / "assets").mkdir()
    (output_path / "zine.yaml").write_text(
        yaml.safe_dump(project_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    (output_path / INVENTORY_FILENAME).write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    review_path = output_path / REVIEW_FILENAME
    review_path.write_text(
        build_review_html(args.project_id, args.title, inbox_path, review_path, candidates),
        encoding="utf-8",
    )
    (output_path / README_FILENAME).write_text(
        project_readme(args.project_id, args.title, inbox_path, len(candidates)),
        encoding="utf-8",
    )
    return output_path, candidates, planned


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create a neutral ZineOS project and inventory a photo inbox."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--inbox", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="New directory under projects/ (default: projects/<project-id>)",
    )
    parser.add_argument("--language", default="en")
    parser.add_argument("--creator", default="")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--top-level-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        output_path, candidates, planned = bootstrap_project(args)
    except (BootstrapError, OSError, yaml.YAMLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    action = "DRY RUN" if args.dry_run else "BOOTSTRAP"
    print(f"{action} ✓ {output_path}")
    print(f"INBOX ✓ {len(candidates)} unassigned image candidate(s)")
    for item in planned:
        print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

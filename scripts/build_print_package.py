#!/usr/bin/env python3

"""Build ZineOS A5 saddle-stitch print data with true 3 mm bleed.

The browser renders each logical page once at finished A5 size. Bleed is added
after CMYK conversion by reflecting only the outermost page edge. Reflected
regions underlap the finished page by a sub-point amount so PDF rasterizers do
not expose a stitching seam at the TrimBox; the opaque finished page is merged
last and remains visually authoritative.
"""

import argparse
from copy import deepcopy
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time

import yaml

from build_preview import build_html


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"
DEFAULT_HTML_PATH = ROOT / "output" / "print" / "ZINE_001_PRINT.html"
DEFAULT_PDF_PATH = ROOT / "output" / "pdf" / "ZINE_001_RGB_PRINT_PROOF.pdf"
DEFAULT_CMYK_PDF_PATH = (
    ROOT / "output" / "pdf" / "ZINE_001_SADDLE_STITCH_CMYK_PRINT.pdf"
)
DEFAULT_REPORT_PATH = ROOT / "output" / "print" / "ZINE_001_RESOLUTION_REPORT.md"
DEFAULT_SPEC_PATH = ROOT / "output" / "print" / "ZINE_001_PRINT_SPEC.txt"

A5_WIDTH_MM = 148
A5_HEIGHT_MM = 210
BLEED_MM = 3
TRIM_SPREAD_WIDTH_MM = A5_WIDTH_MM * 2
BLEED_WIDTH_MM = A5_WIDTH_MM + BLEED_MM * 2
BLEED_HEIGHT_MM = A5_HEIGHT_MM + BLEED_MM * 2
BLEED_SPREAD_WIDTH_MM = TRIM_SPREAD_WIDTH_MM + BLEED_MM * 2
CROP_MARK_MARGIN_MM = 10
CROP_MARK_LENGTH_MM = 7
FINAL_SPREAD_WIDTH_MM = BLEED_SPREAD_WIDTH_MM + CROP_MARK_MARGIN_MM * 2
FINAL_HEIGHT_MM = BLEED_HEIGHT_MM + CROP_MARK_MARGIN_MM * 2
TARGET_DPI = 300
NORMALIZE_OVERSCAN_MM = 0.5
BLEED_SEAM_UNDERLAP_PT = 0.5
IMPOSITION_SEAM_OVERLAP_PT = 0.5

MM = 72 / 25.4
A5_WIDTH_PT = A5_WIDTH_MM * MM
A5_HEIGHT_PT = A5_HEIGHT_MM * MM
BLEED_PT = BLEED_MM * MM
BLEED_WIDTH_PT = BLEED_WIDTH_MM * MM
BLEED_HEIGHT_PT = BLEED_HEIGHT_MM * MM


PRINT_CSS = f"""
<style id="zineos-print-package-styles">
@page {{ size: {A5_WIDTH_PT:.6f}pt {A5_HEIGHT_PT:.6f}pt; margin: 0; }}

html,
body {{
    width: {A5_WIDTH_MM}mm !important;
    min-width: {A5_WIDTH_MM}mm !important;
    max-width: {A5_WIDTH_MM}mm !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden !important;
    background: #fff !important;
}}

.print-publication {{
    width: {A5_WIDTH_MM}mm;
    margin: 0;
    padding: 0;
    overflow: hidden;
}}

.print-page {{
    position: relative;
    width: {A5_WIDTH_MM}mm;
    height: {A5_HEIGHT_MM}mm;
    margin: 0;
    padding: 0;
    overflow: hidden;
    contain: strict;
    break-after: page;
    page-break-after: always;
    background: #fffef9;
}}

.print-page:last-child {{
    break-after: auto;
    page-break-after: auto;
}}

.print-sheet {{
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: {A5_WIDTH_MM}mm !important;
    height: {A5_HEIGHT_MM}mm !important;
    margin: 0 !important;
    border: 0 !important;
    box-shadow: none !important;
    transform: none !important;
}}

.print-sheet-spread {{
    width: {TRIM_SPREAD_WIDTH_MM}mm !important;
}}

.print-sheet-spread-right {{
    left: {-A5_WIDTH_MM}mm !important;
}}

.print-sheet .page-sheet::after,
.print-sheet::after {{
    display: none !important;
}}
</style>
"""


PRINT_SCRIPT = """
<script id="zineos-print-package-runtime">
(() => {
    const source = document.querySelector('.publication');
    const printPublication = document.createElement('main');
    printPublication.className = 'print-publication';
    let logicalPage = 1;

    for (const unit of source.querySelectorAll('.page-unit')) {
        const sheet = unit.querySelector('.page-sheet');
        const isSpread = unit.classList.contains('spread');
        const pageCount = isSpread ? 2 : 1;

        for (let index = 0; index < pageCount; index += 1) {
            const wrapper = document.createElement('section');
            wrapper.className = 'print-page';
            wrapper.dataset.logicalPage = String(logicalPage);

            const clone = sheet.cloneNode(true);
            clone.classList.add('print-sheet');
            if (isSpread) {
                clone.classList.add('print-sheet-spread');
                clone.classList.add(
                    index === 0
                        ? 'print-sheet-spread-left'
                        : 'print-sheet-spread-right'
                );
            } else {
                clone.classList.add('print-sheet-single');
            }
            wrapper.appendChild(clone);
            printPublication.appendChild(wrapper);
            logicalPage += 1;
        }
    }

    printPublication.dataset.pageCount = String(logicalPage - 1);
    document.body.replaceChildren(printPublication);
})();
</script>
"""


FULL_PAGE_LAYOUTS = {
    "full-page",
    "full-page-story",
    "image-with-reflection",
    "image-with-short-text",
}

FULL_SPREAD_LAYOUTS = {
    "full-bleed-spread",
    "full-bleed-story-spread",
}


def load_yaml(path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def logical_page_count(zine_data):
    pages = [
        page_number
        for page_unit in zine_data.get("pages", [])
        for page_number in page_unit.get("pages", [])
    ]
    return max(pages, default=0)


def saddle_stitch_pairs(page_count):
    """Return zero-based imposed page pairs for left-bound saddle stitch."""
    if page_count <= 0 or page_count % 4:
        raise ValueError("Saddle-stitch page count must be a positive multiple of 4")
    pairs = []
    for sheet in range(page_count // 4):
        pairs.append((page_count - 1 - sheet * 2, sheet * 2))
        pairs.append((sheet * 2 + 1, page_count - 2 - sheet * 2))
    return pairs


def inject_print_runtime(preview_html):
    return preview_html.replace(
        "</head>", f"{PRINT_CSS}\n</head>", 1
    ).replace(
        "</body>", f"{PRINT_SCRIPT}\n</body>", 1
    )


def build_print_html(zine_data, zine_path, output_path):
    return inject_print_runtime(build_html(zine_data, zine_path, output_path))


def find_chrome(explicit_path=None):
    candidates = [
        explicit_path,
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def render_pdf(print_html_path, pdf_path, chrome_path):
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="zineos-print-chrome-") as profile:
        command = [
            str(chrome_path),
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path.resolve()}",
            print_html_path.resolve().as_uri(),
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.monotonic() + 180
        previous_size = -1
        stable_checks = 0
        while time.monotonic() < deadline:
            current_size = pdf_path.stat().st_size if pdf_path.is_file() else 0
            if current_size > 0 and current_size == previous_size:
                stable_checks += 1
            else:
                stable_checks = 0
            if stable_checks >= 3:
                break
            return_code = process.poll()
            if return_code not in {None, 0} and current_size == 0:
                raise RuntimeError(
                    f"Chrome PDF export failed with exit code {return_code}."
                )
            previous_size = current_size
            time.sleep(0.25)
        else:
            raise RuntimeError("Chrome PDF export did not finish writing the output file.")
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    with pdf_path.open("rb") as file:
        if file.read(5) != b"%PDF-":
            raise RuntimeError("Chrome PDF export did not produce a valid PDF header.")


def normalize_trim_pdf(pdf_path):
    """Normalize Chrome output to exact A5 pages with no synthetic bleed.

    Chromium can leave a sub-millimeter blank strip at a nominal page edge
    because CSS millimeters are rounded onto PDF coordinates. Scale the single
    finished-page surface slightly past the target box, then clip it to A5.
    This is a uniform output normalization, not a second layout or bleed layer.
    """
    from pypdf import PdfReader, PdfWriter, Transformation
    from pypdf.generic import RectangleObject

    source_path = pdf_path.resolve()
    temporary_path = source_path.with_suffix(".normalized.pdf")
    reader = PdfReader(source_path)
    writer = PdfWriter()
    trim_box = RectangleObject([0, 0, A5_WIDTH_PT, A5_HEIGHT_PT])
    for source_page in reader.pages:
        target_page = writer.add_blank_page(A5_WIDTH_PT, A5_HEIGHT_PT)
        scale_x = (A5_WIDTH_MM + NORMALIZE_OVERSCAN_MM) * MM / float(
            source_page.mediabox.width
        )
        scale_y = (A5_HEIGHT_MM + NORMALIZE_OVERSCAN_MM) * MM / float(
            source_page.mediabox.height
        )
        target_page.merge_transformed_page(
            source_page,
            Transformation().scale(scale_x, scale_y),
            expand=False,
        )
        target_page.mediabox = trim_box
        target_page.cropbox = trim_box
        target_page.trimbox = trim_box
        target_page.bleedbox = trim_box
        target_page.artbox = trim_box
    with temporary_path.open("wb") as output:
        writer.write(output)
    os.replace(temporary_path, source_path)


def validate_icc_profile(icc_profile):
    header = icc_profile.read_bytes()[:128]
    if len(header) < 128 or header[36:40] != b"acsp":
        raise ValueError(f"Not a valid ICC profile: {icc_profile}")
    if header[16:20] != b"CMYK":
        raise ValueError(f"ICC profile is not CMYK: {icc_profile}")


def convert_pdf_to_cmyk(source_pdf, output_pdf, icc_profile, ghostscript):
    validate_icc_profile(icc_profile)
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    output_pdf.unlink(missing_ok=True)
    subprocess.run([
        str(ghostscript),
        "-q",
        "-dNOSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dProcessColorModel=/DeviceCMYK",
        "-sColorConversionStrategy=CMYK",
        "-sColorConversionStrategyForImages=CMYK",
        "-dRenderIntent=0",
        "-dOverrideICC=true",
        f"-sOutputICCProfile={icc_profile.resolve()}",
        f"-sOutputFile={output_pdf.resolve()}",
        str(source_pdf.resolve()),
    ], check=True)


def _merge_region(target, source_page, box, matrix):
    from pypdf import Transformation
    from pypdf.generic import RectangleObject

    region = deepcopy(source_page)
    region.cropbox = RectangleObject(box)
    target.merge_transformed_page(region, Transformation(matrix))


def add_true_bleed(source_pdf, output_pdf):
    """Add reflected 3 mm bleed with a concealed seam-safe underlap."""
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject

    reader = PdfReader(source_pdf)
    writer = PdfWriter()
    width = A5_WIDTH_PT
    height = A5_HEIGHT_PT
    bleed = BLEED_PT
    underlap = BLEED_SEAM_UNDERLAP_PT
    for source_page in reader.pages:
        page = writer.add_blank_page(width=BLEED_WIDTH_PT, height=BLEED_HEIGHT_PT)
        # Reflected regions extend 0.5 pt beneath the opaque finished page.
        # This removes viewer-dependent hairlines without changing TrimBox
        # content, the external 3 mm bleed, or the imposed page geometry.
        # Corners.
        _merge_region(
            page,
            source_page,
            [0, 0, bleed + underlap, bleed + underlap],
            (-1, 0, 0, -1, bleed + underlap, bleed + underlap),
        )
        _merge_region(
            page,
            source_page,
            [width - bleed - underlap, 0, width, bleed + underlap],
            (-1, 0, 0, -1, 2 * width + bleed - underlap, bleed + underlap),
        )
        _merge_region(
            page,
            source_page,
            [0, height - bleed - underlap, bleed + underlap, height],
            (-1, 0, 0, -1, bleed + underlap, 2 * height + bleed - underlap),
        )
        _merge_region(page, source_page,
                      [width - bleed - underlap, height - bleed - underlap,
                       width, height],
                      (-1, 0, 0, -1, 2 * width + bleed - underlap,
                       2 * height + bleed - underlap))
        # Edge strips.
        _merge_region(page, source_page, [0, 0, bleed + underlap, height],
                      (-1, 0, 0, 1, bleed + underlap, bleed))
        _merge_region(
            page,
            source_page,
            [width - bleed - underlap, 0, width, height],
            (-1, 0, 0, 1, 2 * width + bleed - underlap, bleed),
        )
        _merge_region(page, source_page, [0, 0, width, bleed + underlap],
                      (1, 0, 0, -1, bleed, bleed + underlap))
        _merge_region(
            page,
            source_page,
            [0, height - bleed - underlap, width, height],
            (1, 0, 0, -1, bleed, 2 * height + bleed - underlap),
        )
        # Finished page is merged last and remains unchanged inside TrimBox.
        _merge_region(page, source_page, [0, 0, width, height],
                      (1, 0, 0, 1, bleed, bleed))
        page.mediabox = RectangleObject([0, 0, BLEED_WIDTH_PT, BLEED_HEIGHT_PT])
        page.cropbox = page.mediabox
        page.bleedbox = page.mediabox
        page.trimbox = RectangleObject([
            bleed, bleed, bleed + width, bleed + height
        ])
        page.artbox = page.trimbox
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as output:
        writer.write(output)


def _add_crop_marks(page, writer):
    from pypdf.generic import DecodedStreamObject, NameObject

    bleed_left = CROP_MARK_MARGIN_MM * MM
    bleed_bottom = CROP_MARK_MARGIN_MM * MM
    bleed_right = bleed_left + BLEED_SPREAD_WIDTH_MM * MM
    bleed_top = bleed_bottom + BLEED_HEIGHT_MM * MM
    trim_left = bleed_left + BLEED_PT
    trim_bottom = bleed_bottom + BLEED_PT
    trim_right = trim_left + TRIM_SPREAD_WIDTH_MM * MM
    trim_top = trim_bottom + A5_HEIGHT_PT
    outer = CROP_MARK_LENGTH_MM * MM
    lines = []
    for start, end in (
        (bleed_left - outer, bleed_left),
        (bleed_right, bleed_right + outer),
    ):
        for y in (bleed_bottom, trim_bottom, trim_top, bleed_top):
            lines.append((start, y, end, y))
    for start, end in (
        (bleed_bottom - outer, bleed_bottom),
        (bleed_top, bleed_top + outer),
    ):
        for x in (bleed_left, trim_left, trim_right, bleed_right):
            lines.append((x, start, x, end))
    commands = ["q", "0 0 0 1 K", "0.25 w"]
    commands.extend(
        f"{x1:.4f} {y1:.4f} m {x2:.4f} {y2:.4f} l S"
        for x1, y1, x2, y2 in lines
    )
    commands.append("Q")
    stream = DecodedStreamObject()
    stream.set_data(("\n".join(commands) + "\n").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)


def _add_output_intent(writer, icc_profile):
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    profile = DecodedStreamObject()
    profile.set_data(icc_profile.read_bytes())
    profile[NameObject("/N")] = NumberObject(4)
    profile_reference = writer._add_object(profile)
    intent = DictionaryObject({
        NameObject("/Type"): NameObject("/OutputIntent"),
        NameObject("/S"): NameObject("/GTS_PDFX"),
        NameObject("/OutputConditionIdentifier"): TextStringObject(
            "Japan Color 2011 Coated"
        ),
        NameObject("/RegistryName"): TextStringObject(
            "https://registry.color.org/"
        ),
        NameObject("/Info"): TextStringObject(
            "JapanColor2011Coated.icc; perceptual RGB-to-CMYK conversion"
        ),
        NameObject("/DestOutputProfile"): profile_reference,
    })
    writer.root_object[NameObject("/OutputIntents")] = ArrayObject([
        writer._add_object(intent)
    ])


def impose_saddle_stitch(source_pdf, output_pdf, icc_profile, title):
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject

    reader = PdfReader(source_pdf)
    pairs = saddle_stitch_pairs(len(reader.pages))
    writer = PdfWriter()
    writer.pdf_header = "%PDF-1.4"
    media_width = FINAL_SPREAD_WIDTH_MM * MM
    media_height = FINAL_HEIGHT_MM * MM
    mark_margin = CROP_MARK_MARGIN_MM * MM
    trim_left = mark_margin + BLEED_PT
    trim_bottom = mark_margin + BLEED_PT
    trim_right = trim_left + TRIM_SPREAD_WIDTH_MM * MM
    trim_top = trim_bottom + A5_HEIGHT_PT
    bleed_right = mark_margin + BLEED_SPREAD_WIDTH_MM * MM
    bleed_top = mark_margin + BLEED_HEIGHT_PT
    seam_overlap = IMPOSITION_SEAM_OVERLAP_PT

    for left_index, right_index in pairs:
        page = writer.add_blank_page(width=media_width, height=media_height)
        _add_crop_marks(page, writer)
        left = deepcopy(reader.pages[left_index])
        left.cropbox = RectangleObject([
            0, 0,
            BLEED_PT + A5_WIDTH_PT + seam_overlap,
            BLEED_HEIGHT_PT,
        ])
        page.merge_translated_page(left, mark_margin, mark_margin)
        right = deepcopy(reader.pages[right_index])
        right.cropbox = RectangleObject([
            BLEED_PT - seam_overlap, 0,
            BLEED_WIDTH_PT, BLEED_HEIGHT_PT,
        ])
        page.merge_translated_page(
            right, mark_margin + A5_WIDTH_PT, mark_margin
        )
        page.cropbox = RectangleObject([0, 0, media_width, media_height])
        page.bleedbox = RectangleObject([
            mark_margin, mark_margin, bleed_right, bleed_top
        ])
        page.trimbox = RectangleObject([
            trim_left, trim_bottom, trim_right, trim_top
        ])
        page.artbox = page.trimbox

    _add_output_intent(writer, icc_profile)
    writer.add_metadata({
        "/Title": f"{title} - A5 Saddle-Stitch CMYK Print Data",
        "/Creator": "ZineOS",
        "/Subject": (
            f"A5 left-bound saddle stitch; {len(reader.pages)} pages; "
            "continuous 3 mm bleed; crop marks; Japan Color 2011 Coated CMYK"
        ),
    })
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as output:
        writer.write(output)


def build_cmyk_print_pdf(rgb_pdf, cmyk_pdf, icc_profile, ghostscript, title):
    validate_icc_profile(icc_profile)
    with tempfile.TemporaryDirectory(prefix="zineos-print-cmyk-") as temp_dir:
        temp_path = Path(temp_dir)
        cmyk_trim = temp_path / "trim-cmyk.pdf"
        cmyk_bleed = temp_path / "bleed-cmyk.pdf"
        convert_pdf_to_cmyk(rgb_pdf, cmyk_trim, icc_profile, ghostscript)
        add_true_bleed(cmyk_trim, cmyk_bleed)
        impose_saddle_stitch(cmyk_bleed, cmyk_pdf, icc_profile, title)


def jpeg_dimensions(path):
    with path.open("rb") as file:
        if file.read(2) != b"\xff\xd8":
            return None
        while True:
            marker_start = file.read(1)
            if not marker_start:
                return None
            if marker_start != b"\xff":
                continue
            marker = file.read(1)
            while marker == b"\xff":
                marker = file.read(1)
            if marker in {b"\xd8", b"\xd9"}:
                continue
            length_bytes = file.read(2)
            if len(length_bytes) != 2:
                return None
            length = struct.unpack(">H", length_bytes)[0]
            if marker[0] in {
                0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
            }:
                data = file.read(length - 2)
                if len(data) < 5:
                    return None
                height, width = struct.unpack(">HH", data[1:5])
                return width, height
            file.seek(length - 2, 1)


def image_dimensions(path):
    suffix = path.suffix.lower()
    if suffix == ".png":
        with path.open("rb") as file:
            header = file.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n" or len(header) < 24:
            return None
        return struct.unpack(">II", header[16:24])
    if suffix in {".jpg", ".jpeg"}:
        return jpeg_dimensions(path)
    if suffix == ".svg":
        return "vector"
    return None


def iter_asset_usages(zine_data):
    for page_unit in zine_data.get("pages", []):
        page_label = "-".join(str(page) for page in page_unit.get("pages", []))
        layout_type = page_unit.get("layout", {}).get("type", "unspecified")
        layout = page_unit.get("layout", {})
        if layout_type in {"memory-index-grid", "closing-memory-grid"}:
            for asset_id in layout.get("settings", {}).get("assets", []):
                yield page_label, layout_type, asset_id, "grid"
        for block in page_unit.get("blocks", []):
            block_type = block.get("type")
            asset_ids = []
            if block_type in {"PHOTO", "MAP"} and block.get("asset"):
                asset_ids = [block["asset"]]
            elif block_type == "GALLERY":
                asset_ids = block.get("assets", [])
            for asset_id in asset_ids:
                if block_type == "MAP":
                    placement = "vector-background"
                elif layout_type in FULL_SPREAD_LAYOUTS:
                    placement = "full-spread"
                elif layout_type in FULL_PAGE_LAYOUTS:
                    placement = "full-page"
                else:
                    placement = "layout-specific"
                yield page_label, layout_type, asset_id, placement


def estimated_dpi(dimensions, placement):
    if dimensions in {None, "vector"}:
        return None
    width, height = dimensions
    if placement == "full-page":
        physical_width, physical_height = A5_WIDTH_MM, A5_HEIGHT_MM
    elif placement == "full-spread":
        physical_width, physical_height = TRIM_SPREAD_WIDTH_MM, A5_HEIGHT_MM
    else:
        return None
    return min(width / (physical_width / 25.4), height / (physical_height / 25.4))


def resolution_state(dpi, dimensions):
    if dimensions == "vector":
        return "VECTOR"
    if dpi is None:
        return "MANUAL"
    if dpi >= TARGET_DPI:
        return "PASS"
    if dpi >= 240:
        return "CAUTION"
    return "LOW"


def build_resolution_report(zine_data, zine_path):
    assets = {
        asset.get("id"): asset
        for asset in zine_data.get("assets", [])
        if asset.get("id")
    }
    lines = [
        "# ZINE_001 Print Resolution Report",
        "",
        f"- Target: {TARGET_DPI} dpi",
        f"- Trim: A5 ({A5_WIDTH_MM} x {A5_HEIGHT_MM} mm)",
        f"- Bleed: {BLEED_MM} mm outside TrimBox",
        f"- Logical pages: {logical_page_count(zine_data)}",
        "- Color: Japan Color 2011 Coated CMYK plus an RGB review proof.",
        "",
        "| Pages | Layout | Asset | Source | Placement | Estimated dpi | State |",
        "| --- | --- | --- | ---: | --- | ---: | --- |",
    ]
    zine_dir = zine_path.parent
    for page_label, layout_type, asset_id, placement in iter_asset_usages(zine_data):
        asset = assets.get(asset_id, {})
        source = asset.get("source")
        asset_path = (zine_dir / source).resolve() if source else None
        if asset_path and asset_path.is_file():
            dimensions = image_dimensions(asset_path)
            source_label = (
                "vector" if dimensions == "vector"
                else f"{dimensions[0]}x{dimensions[1]}" if dimensions
                else "unknown"
            )
        else:
            dimensions = None
            source_label = "missing"
        dpi = estimated_dpi(dimensions, placement)
        dpi_label = f"{dpi:.0f}" if dpi is not None else "-"
        state = "MISSING" if source_label == "missing" else resolution_state(
            dpi, dimensions
        )
        lines.append(
            f"| {page_label} | {layout_type} | {asset_id} | {source_label} | "
            f"{placement} | {dpi_label} | {state} |"
        )
    lines.extend([
        "",
        "Current ZINE_001 image resolution was accepted by the creator after a physical proof.",
        "",
    ])
    return "\n".join(lines)


def build_print_spec(zine_data):
    page_count = logical_page_count(zine_data)
    return "\n".join([
        "ZINEOS A5 SADDLE-STITCH PRINT SPEC",
        "",
        "Format: A5 portrait, left-bound saddle stitch",
        f"Logical pages: {page_count}",
        f"Imposed sides: {page_count // 2}",
        f"Trim size per page: {A5_WIDTH_MM} x {A5_HEIGHT_MM} mm",
        f"Bleed: {BLEED_MM} mm outside TrimBox; "
        "seam-safe underlap concealed beneath trim",
        f"Imposed TrimBox: {TRIM_SPREAD_WIDTH_MM} x {A5_HEIGHT_MM} mm",
        f"Imposed BleedBox: {BLEED_SPREAD_WIDTH_MM} x {BLEED_HEIGHT_MM} mm",
        f"MediaBox with crop marks: {FINAL_SPREAD_WIDTH_MM} x {FINAL_HEIGHT_MM} mm",
        "Crop marks: outside BleedBox",
        "Color: CMYK, Japan Color 2011 Coated OutputIntent",
        "Rendering intent: perceptual",
        "Fonts: embedded",
        "Output: one imposed PDF in printer order",
        "",
    ])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build standard ZineOS A5 saddle-stitch print data."
    )
    parser.add_argument("zine", nargs="?", type=Path, default=DEFAULT_ZINE_PATH)
    parser.add_argument("html", nargs="?", type=Path, default=DEFAULT_HTML_PATH)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF_PATH)
    parser.add_argument("--cmyk-pdf", type=Path, default=DEFAULT_CMYK_PDF_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--icc-profile", type=Path)
    parser.add_argument("--ghostscript", type=Path)
    parser.add_argument("--chrome", type=Path)
    parser.add_argument(
        "--html-only", action="store_true",
        help="Build print HTML, report, and specification without PDF export.",
    )
    return parser.parse_args(argv)


def resolve_repo_path(path):
    return path if path.is_absolute() else ROOT / path


def main(argv=None):
    args = parse_args(argv)
    zine_path = resolve_repo_path(args.zine).resolve()
    html_path = resolve_repo_path(args.html).resolve()
    pdf_path = resolve_repo_path(args.pdf).resolve()
    cmyk_pdf_path = resolve_repo_path(args.cmyk_pdf).resolve()
    report_path = resolve_repo_path(args.report).resolve()
    spec_path = resolve_repo_path(args.spec).resolve()
    if not zine_path.is_file():
        print(f"ERROR: Zine file not found: {zine_path}")
        return 2

    zine_data = load_yaml(zine_path)
    page_count = logical_page_count(zine_data)
    try:
        saddle_stitch_pairs(page_count)
    except ValueError as error:
        print(f"ERROR: {error}: {page_count}")
        return 2

    html_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(build_print_html(zine_data, zine_path, html_path), encoding="utf-8")
    report_path.write_text(build_resolution_report(zine_data, zine_path), encoding="utf-8")
    spec_path.write_text(build_print_spec(zine_data), encoding="utf-8")
    print(f"PRINT HTML PASS: {html_path}")
    print(f"RESOLUTION REPORT PASS: {report_path}")
    print(f"PRINT SPEC PASS: {spec_path}")

    if args.html_only:
        return 0
    chrome_path = find_chrome(args.chrome)
    if chrome_path is None:
        print("ERROR: Chrome or Chromium is required for PDF export.")
        return 2
    render_pdf(html_path, pdf_path, chrome_path)
    normalize_trim_pdf(pdf_path)
    print(f"RGB A5 PROOF PASS: {pdf_path}")

    if args.icc_profile is None:
        print("ERROR: --icc-profile is required for standard CMYK print output.")
        return 2
    icc_profile = resolve_repo_path(args.icc_profile).resolve()
    if not icc_profile.is_file():
        print(f"ERROR: ICC profile not found: {icc_profile}")
        return 2
    ghostscript = args.ghostscript or shutil.which("gs")
    if not ghostscript:
        print("ERROR: Ghostscript is required for CMYK PDF export.")
        return 2
    title = zine_data.get("project", {}).get("title", zine_path.stem)
    build_cmyk_print_pdf(
        pdf_path, cmyk_pdf_path, icc_profile, Path(ghostscript), title
    )
    print(f"STANDARD CMYK PRINT PDF PASS: {cmyk_pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

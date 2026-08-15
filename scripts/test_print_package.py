#!/usr/bin/env python3

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_print_package import (
    A5_HEIGHT_MM,
    A5_HEIGHT_PT,
    A5_WIDTH_MM,
    A5_WIDTH_PT,
    BLEED_HEIGHT_MM,
    BLEED_HEIGHT_PT,
    BLEED_MM,
    BLEED_SPREAD_WIDTH_MM,
    BLEED_WIDTH_PT,
    CROP_MARK_MARGIN_MM,
    FINAL_HEIGHT_MM,
    FINAL_SPREAD_WIDTH_MM,
    PRINT_SCRIPT,
    NORMALIZE_OVERSCAN_MM,
    add_true_bleed,
    build_print_html,
    build_print_spec,
    build_resolution_report,
    image_dimensions,
    impose_saddle_stitch,
    load_yaml,
    logical_page_count,
    normalize_trim_pdf,
    render_pdf,
    saddle_stitch_pairs,
    validate_icc_profile,
)


ROOT = Path(__file__).resolve().parents[1]
ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"
MM = 72 / 25.4


class PrintPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.zine_data = load_yaml(ZINE_PATH)

    def test_zine_001_is_saddle_stitch_compatible(self):
        page_count = logical_page_count(self.zine_data)
        self.assertEqual(page_count, 28)
        self.assertEqual(page_count % 4, 0)

    def test_generic_saddle_stitch_order(self):
        self.assertEqual(
            saddle_stitch_pairs(28),
            [
                (27, 0), (1, 26), (25, 2), (3, 24),
                (23, 4), (5, 22), (21, 6), (7, 20),
                (19, 8), (9, 18), (17, 10), (11, 16),
                (15, 12), (13, 14),
            ],
        )
        self.assertEqual(saddle_stitch_pairs(4), [(3, 0), (1, 2)])
        with self.assertRaises(ValueError):
            saddle_stitch_pairs(6)

    def test_print_html_renders_one_trim_layer_per_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "ZINE_001_PRINT.html"
            rendered = build_print_html(self.zine_data, ZINE_PATH, output_path)
        self.assertIn(
            f"@page {{ size: {A5_WIDTH_PT:.6f}pt {A5_HEIGHT_PT:.6f}pt; margin: 0; }}",
            rendered,
        )
        self.assertEqual(PRINT_SCRIPT.count("cloneNode(true)"), 1)
        self.assertIn("print-sheet-single", rendered)
        self.assertNotIn(".print-sheet-single {", rendered)
        self.assertNotIn("print-sheet-bleed", rendered)
        self.assertNotIn("for (const layer", rendered)
        self.assertNotIn("transform: scale(", rendered)

    def test_normalized_browser_pdf_is_exact_a5_without_synthetic_bleed(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ContentStream, DecodedStreamObject, NameObject

        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "proof.pdf"
            writer = PdfWriter()
            source_page = writer.add_blank_page(
                width=A5_WIDTH_PT, height=A5_HEIGHT_PT
            )
            stream = DecodedStreamObject()
            stream.set_data(
                f"0 0 0 rg 0 0 {A5_WIDTH_PT} {A5_HEIGHT_PT} re f".encode()
            )
            source_page[NameObject("/Contents")] = writer._add_object(stream)
            with pdf_path.open("wb") as output:
                writer.write(output)
            normalize_trim_pdf(pdf_path)
            reader = PdfReader(pdf_path)
            page = reader.pages[0]
            transforms = [
                operands
                for operands, operator in ContentStream(
                    page.get_contents(), reader
                ).operations
                if operator == b"cm"
            ]
        self.assertAlmostEqual(float(page.mediabox.width), A5_WIDTH_PT, places=3)
        self.assertAlmostEqual(float(page.mediabox.height), A5_HEIGHT_PT, places=3)
        self.assertEqual(list(page.trimbox), list(page.mediabox))
        self.assertEqual(list(page.bleedbox), list(page.mediabox))
        self.assertAlmostEqual(
            float(transforms[0][0]),
            (A5_WIDTH_MM + NORMALIZE_OVERSCAN_MM) / A5_WIDTH_MM,
            places=6,
        )
        self.assertAlmostEqual(
            float(transforms[0][3]),
            (A5_HEIGHT_MM + NORMALIZE_OVERSCAN_MM) / A5_HEIGHT_MM,
            places=6,
        )

    def test_true_bleed_is_added_outside_a5_trim(self):
        from pypdf import PdfReader, PdfWriter

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "trim.pdf"
            output = Path(temp_dir) / "bleed.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=A5_WIDTH_PT, height=A5_HEIGHT_PT)
            with source.open("wb") as stream:
                writer.write(stream)
            add_true_bleed(source, output)
            page = PdfReader(output).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width), BLEED_WIDTH_PT, places=3)
        self.assertAlmostEqual(float(page.mediabox.height), BLEED_HEIGHT_PT, places=3)
        self.assertAlmostEqual(float(page.trimbox.left), BLEED_MM * MM, places=3)
        self.assertAlmostEqual(float(page.trimbox.bottom), BLEED_MM * MM, places=3)
        self.assertAlmostEqual(float(page.trimbox.width), A5_WIDTH_PT, places=3)
        self.assertAlmostEqual(float(page.trimbox.height), A5_HEIGHT_PT, places=3)

    def test_imposed_pdf_has_standard_boxes_and_output_intent(self):
        from pypdf import PdfReader, PdfWriter

        with tempfile.TemporaryDirectory() as temp_dir:
            profile = Path(temp_dir) / "test-cmyk.icc"
            header = bytearray(128)
            header[16:20] = b"CMYK"
            header[36:40] = b"acsp"
            profile.write_bytes(header)
            source = Path(temp_dir) / "bleed.pdf"
            output = Path(temp_dir) / "imposed.pdf"
            writer = PdfWriter()
            for _ in range(4):
                page = writer.add_blank_page(
                    width=BLEED_WIDTH_PT, height=BLEED_HEIGHT_PT
                )
                page.trimbox.lower_left = (BLEED_MM * MM, BLEED_MM * MM)
                page.trimbox.upper_right = (
                    (BLEED_MM + A5_WIDTH_MM) * MM,
                    (BLEED_MM + A5_HEIGHT_MM) * MM,
                )
            with source.open("wb") as stream:
                writer.write(stream)
            impose_saddle_stitch(source, output, profile, "Test Zine")
            reader = PdfReader(output)
            page = reader.pages[0]
            intent = reader.trailer["/Root"]["/OutputIntents"][0].get_object()
        self.assertEqual(len(reader.pages), 2)
        self.assertAlmostEqual(
            float(page.mediabox.width), FINAL_SPREAD_WIDTH_MM * MM, places=3
        )
        self.assertAlmostEqual(
            float(page.mediabox.height), FINAL_HEIGHT_MM * MM, places=3
        )
        self.assertAlmostEqual(
            float(page.bleedbox.width), BLEED_SPREAD_WIDTH_MM * MM, places=3
        )
        self.assertAlmostEqual(float(page.trimbox.width), 296 * MM, places=3)
        self.assertAlmostEqual(
            float(page.bleedbox.left), CROP_MARK_MARGIN_MM * MM, places=3
        )
        self.assertEqual(
            intent["/OutputConditionIdentifier"], "Japan Color 2011 Coated"
        )
        self.assertEqual(intent["/DestOutputProfile"].get_object()["/N"], 4)

    def test_icc_validation_rejects_non_profile_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.icc"
            path.write_bytes(b"not an icc profile")
            with self.assertRaises(ValueError):
                validate_icc_profile(path)

    def test_resolution_report_records_known_risks(self):
        report = build_resolution_report(self.zine_data, ZINE_PATH)
        self.assertIn(
            "| 8-9 | full-bleed-spread | photo-006 | 1536x2048 | full-spread | 132 | LOW |",
            report,
        )
        self.assertIn(
            "| 12 | full-page | photo-008 | 1536x2048 | full-page | 248 | CAUTION |",
            report,
        )
        self.assertIn(
            "| 4-5 | trace-map-spread | map-001 | vector | vector-background | - | VECTOR |",
            report,
        )

    def test_png_dimensions_are_read_without_image_dependency(self):
        path = ROOT / "examples" / "ZINE_001" / "assets" / "bottle-001.png"
        self.assertEqual(image_dimensions(path), (420, 1220))

    def test_pdf_export_removes_stale_output_before_launch(self):
        class FinishedProcess:
            def poll(self):
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            html_path = temp_path / "proof.html"
            pdf_path = temp_path / "proof.pdf"
            html_path.write_text("<html></html>", encoding="utf-8")
            pdf_path.write_bytes(b"stale output")

            def fake_popen(*args, **kwargs):
                self.assertFalse(pdf_path.exists())
                pdf_path.write_bytes(b"%PDF-new output")
                return FinishedProcess()

            with patch("build_print_package.subprocess.Popen", side_effect=fake_popen), patch(
                "build_print_package.time.sleep"
            ):
                render_pdf(html_path, pdf_path, Path("/fake/chrome"))
            self.assertEqual(pdf_path.read_bytes(), b"%PDF-new output")

    def test_print_spec_records_creator_approved_standard(self):
        spec = build_print_spec(self.zine_data)
        self.assertIn("Format: A5 portrait, left-bound saddle stitch", spec)
        self.assertIn("Logical pages: 28", spec)
        self.assertIn("Imposed sides: 14", spec)
        self.assertIn("Bleed: 3 mm outside TrimBox; no overlap inside trim", spec)
        self.assertIn("Imposed TrimBox: 296 x 210 mm", spec)
        self.assertIn("Imposed BleedBox: 302 x 216 mm", spec)
        self.assertIn("MediaBox with crop marks: 322 x 236 mm", spec)
        self.assertIn("Japan Color 2011 Coated", spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)

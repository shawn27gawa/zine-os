#!/usr/bin/env python3

import tempfile
import unittest
from copy import deepcopy
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
    BLEED_SEAM_UNDERLAP_PT,
    BLEED_SPREAD_WIDTH_MM,
    BLEED_WIDTH_PT,
    CROP_MARK_MARGIN_MM,
    CROP_MARK_LENGTH_MM,
    CROP_MARK_LINE_WIDTH_PT,
    FINAL_HEIGHT_MM,
    FINAL_SPREAD_WIDTH_MM,
    IMPOSITION_SEAM_OVERLAP_PT,
    PRINT_SCRIPT,
    NORMALIZE_OVERSCAN_MM,
    _add_crop_marks,
    add_true_bleed,
    build_print_html,
    build_print_spec,
    build_resolution_report,
    default_artifact_paths,
    image_dimensions,
    impose_saddle_stitch,
    load_yaml,
    logical_page_count,
    normalize_trim_pdf,
    render_pdf,
    saddle_stitch_pairs,
    validate_icc_profile,
    validate_standard_print_configuration,
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

    def test_standard_print_configuration_accepts_supported_contract(self):
        self.assertEqual(
            validate_standard_print_configuration(self.zine_data), []
        )

    def test_standard_print_configuration_rejects_unsafe_assumptions(self):
        zine = deepcopy(self.zine_data)
        zine["output"].update({
            "page_size": "Letter",
            "orientation": "landscape",
            "binding": "perfect-bound",
            "bleed_mm": 0,
            "color_mode": "RGB",
        })
        zine["pages"][1]["pages"] = [1, 3]
        errors = validate_standard_print_configuration(zine)
        joined = "\n".join(errors)
        self.assertIn("output.page_size", joined)
        self.assertIn("output.orientation", joined)
        self.assertIn("output.binding", joined)
        self.assertIn("output.bleed_mm", joined)
        self.assertIn("output.color_mode", joined)
        self.assertIn("duplicates", joined)
        self.assertIn("missing", joined)

    def test_default_artifact_paths_are_project_specific(self):
        paths = default_artifact_paths("field-notes-002")
        self.assertEqual(paths["html"].name, "FIELD_NOTES_002_PRINT.html")
        self.assertEqual(
            paths["cmyk_pdf"].name,
            "FIELD_NOTES_002_SADDLE_STITCH_CMYK_PRINT.pdf",
        )
        self.assertNotIn("ZINE_001", "\n".join(str(path) for path in paths.values()))

        unsafe = default_artifact_paths("../Field Notes")
        self.assertTrue(all(".." not in path.name for path in unsafe.values()))
        self.assertTrue(all(path.resolve().is_relative_to(ROOT) for path in unsafe.values()))

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

    def test_true_bleed_underlaps_trim_without_changing_finished_geometry(self):
        from pypdf import PdfWriter

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "trim.pdf"
            output = Path(temp_dir) / "bleed.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=A5_WIDTH_PT, height=A5_HEIGHT_PT)
            with source.open("wb") as stream:
                writer.write(stream)
            with patch("build_print_package._merge_region") as merge_region:
                add_true_bleed(source, output)

        calls = merge_region.call_args_list
        self.assertEqual(len(calls), 9)
        left_edge_box = calls[4].args[2]
        left_edge_matrix = calls[4].args[3]
        finished_box = calls[-1].args[2]
        finished_matrix = calls[-1].args[3]
        self.assertAlmostEqual(
            left_edge_box[2], BLEED_MM * MM + BLEED_SEAM_UNDERLAP_PT
        )
        self.assertAlmostEqual(
            left_edge_matrix[4], BLEED_MM * MM + BLEED_SEAM_UNDERLAP_PT
        )
        self.assertEqual(finished_box, [0, 0, A5_WIDTH_PT, A5_HEIGHT_PT])
        self.assertEqual(
            finished_matrix, (1, 0, 0, 1, BLEED_MM * MM, BLEED_MM * MM)
        )

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

    def test_imposition_pages_overlap_at_fold_without_changing_page_boxes(self):
        from pypdf import PdfWriter

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
                writer.add_blank_page(
                    width=BLEED_WIDTH_PT, height=BLEED_HEIGHT_PT
                )
            with source.open("wb") as stream:
                writer.write(stream)

            captured = []

            def capture_merge(page, translated_page, tx, ty):
                captured.append((list(translated_page.cropbox), tx, ty))

            with patch(
                "pypdf._page.PageObject.merge_translated_page",
                autospec=True,
                side_effect=capture_merge,
            ):
                impose_saddle_stitch(source, output, profile, "Test Zine")

        left_box, left_tx, _ = captured[0]
        right_box, right_tx, _ = captured[1]
        left_edge = left_tx + float(left_box[2])
        right_edge = right_tx + float(right_box[0])
        self.assertAlmostEqual(
            left_edge - right_edge, 2 * IMPOSITION_SEAM_OVERLAP_PT
        )
        self.assertGreater(left_edge, right_edge)

    def test_crop_marks_are_paired_and_stop_at_bleedbox(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ContentStream

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "marks.pdf"
            writer = PdfWriter()
            page = writer.add_blank_page(
                width=FINAL_SPREAD_WIDTH_MM * MM,
                height=FINAL_HEIGHT_MM * MM,
            )
            _add_crop_marks(page, writer)
            with output.open("wb") as stream:
                writer.write(stream)
            reader = PdfReader(output)
            operations = ContentStream(
                reader.pages[0].get_contents(), reader
            ).operations

        points = []
        segments = []
        line_width = None
        line_cap = None
        for operands, operator in operations:
            if operator == b"w":
                line_width = float(operands[0])
            elif operator == b"J":
                line_cap = int(operands[0])
            elif operator == b"m":
                points = [float(operands[0]), float(operands[1])]
            elif operator == b"l":
                end = [float(operands[0]), float(operands[1])]
                segments.append((*points, *end))

        bleed_left = CROP_MARK_MARGIN_MM * MM
        bleed_bottom = CROP_MARK_MARGIN_MM * MM
        bleed_right = bleed_left + BLEED_SPREAD_WIDTH_MM * MM
        bleed_top = bleed_bottom + BLEED_HEIGHT_MM * MM
        trim_left = bleed_left + BLEED_MM * MM
        trim_bottom = bleed_bottom + BLEED_MM * MM
        trim_right = trim_left + A5_WIDTH_MM * 2 * MM
        trim_top = trim_bottom + A5_HEIGHT_MM * MM
        self.assertEqual(line_width, CROP_MARK_LINE_WIDTH_PT)
        self.assertEqual(line_cap, 0)
        self.assertEqual(len(segments), 16)
        tolerance = 0.001
        horizontal_levels = set()
        vertical_levels = set()
        for x1, y1, x2, y2 in segments:
            self.assertAlmostEqual(
                max(abs(x2 - x1), abs(y2 - y1)),
                CROP_MARK_LENGTH_MM * MM,
                places=3,
            )
            if abs(y2 - y1) <= tolerance:
                horizontal_levels.add(round(y1, 3))
                self.assertTrue(
                    abs(y1 - bleed_bottom) <= tolerance
                    or abs(y1 - trim_bottom) <= tolerance
                    or abs(y1 - trim_top) <= tolerance
                    or abs(y1 - bleed_top) <= tolerance
                )
                stops_at_bleed = (
                    abs(max(x1, x2) - bleed_left) <= tolerance
                    or abs(min(x1, x2) - bleed_right) <= tolerance
                )
            else:
                self.assertAlmostEqual(x1, x2, places=3)
                vertical_levels.add(round(x1, 3))
                self.assertTrue(
                    abs(x1 - bleed_left) <= tolerance
                    or abs(x1 - trim_left) <= tolerance
                    or abs(x1 - trim_right) <= tolerance
                    or abs(x1 - bleed_right) <= tolerance
                )
                stops_at_bleed = (
                    abs(max(y1, y2) - bleed_bottom) <= tolerance
                    or abs(min(y1, y2) - bleed_top) <= tolerance
                )
            self.assertTrue(stops_at_bleed)
        self.assertEqual(len(horizontal_levels), 4)
        self.assertEqual(len(vertical_levels), 4)
        for expected in (bleed_bottom, trim_bottom, trim_top, bleed_top):
            self.assertTrue(
                any(abs(actual - expected) <= 0.002 for actual in horizontal_levels)
            )
        for expected in (bleed_left, trim_left, trim_right, bleed_right):
            self.assertTrue(
                any(abs(actual - expected) <= 0.002 for actual in vertical_levels)
            )
        self.assertAlmostEqual(trim_bottom - bleed_bottom, BLEED_MM * MM)
        self.assertAlmostEqual(bleed_top - trim_top, BLEED_MM * MM)
        self.assertAlmostEqual(trim_left - bleed_left, BLEED_MM * MM)
        self.assertAlmostEqual(bleed_right - trim_right, BLEED_MM * MM)

    def test_icc_validation_rejects_non_profile_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.icc"
            path.write_bytes(b"not an icc profile")
            with self.assertRaises(ValueError):
                validate_icc_profile(path)

    def test_resolution_report_records_known_risks(self):
        report = build_resolution_report(self.zine_data, ZINE_PATH)
        self.assertIn("# Our Memory Print Resolution Report", report)
        self.assertNotIn("ZINE_001", report)
        self.assertIn("Physical proof status must be recorded separately", report)
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
        self.assertIn(
            "Bleed: 3 mm outside TrimBox; seam-safe underlap concealed beneath trim",
            spec,
        )
        self.assertIn("Imposed TrimBox: 296 x 210 mm", spec)
        self.assertIn("Imposed BleedBox: 302 x 216 mm", spec)
        self.assertIn("MediaBox with crop marks: 322 x 236 mm", spec)
        self.assertIn(
            "Crop marks: paired inner/outer marks; 3 mm separation; "
            "butt-capped at the BleedBox boundary",
            spec,
        )
        self.assertIn("Japan Color 2011 Coated", spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)

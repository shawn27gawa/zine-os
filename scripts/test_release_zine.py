#!/usr/bin/env python3

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml

import release_zine as release_module
from release_zine import ReleaseError, release, safe_release_output


def release_args(zine, output, mode="review"):
    return argparse.Namespace(
        zine=zine,
        mode=mode,
        output=output,
        icc_profile=None,
        ghostscript=None,
        chrome=None,
    )


class ReleaseZineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zineos-release-test-")
        self.root = Path(self.temporary.name).resolve()
        self.original_root = release_module.ROOT
        self.original_release_root = release_module.RELEASE_ROOT
        release_module.ROOT = self.root
        release_module.RELEASE_ROOT = self.root / "output" / "releases"
        project = self.root / "projects" / "test-zine"
        project.mkdir(parents=True)
        self.zine = project / "zine.yaml"
        self.zine.write_text(
            yaml.safe_dump({
                "project": {"id": "test-zine", "title": "Test Zine"},
                "pages": [
                    {"id": f"page-{page}", "pages": [page], "blocks": [],
                     "layout": {"type": "minimal"}}
                    for page in range(1, 5)
                ],
                "output": {
                    "medium": "print",
                    "page_size": "A5",
                    "orientation": "portrait",
                    "binding": "saddle-stitch",
                    "bleed_mm": 3,
                },
            }, sort_keys=False),
            encoding="utf-8",
        )
        self.output = self.root / "output" / "releases" / "test-release"

    def tearDown(self):
        release_module.ROOT = self.original_root
        release_module.RELEASE_ROOT = self.original_release_root
        self.temporary.cleanup()

    def patches(self, asset_status="PASS", regression_error=None, build_error=None):
        asset_report = {
            "status": asset_status,
            "zine": str(self.zine),
            "assets": 0,
            "references": 0,
            "errors": [] if asset_status == "PASS" else ["broken asset"],
            "warnings": [],
        }

        def preview_builder(data, zine_path, output_path):
            if build_error == "preview":
                raise ReleaseError("preview failed")
            output_path.write_text("preview", encoding="utf-8")

        def studio_builder(data, zine_path, output_path):
            if build_error == "studio":
                raise ReleaseError("studio failed")
            output_path.write_text("studio", encoding="utf-8")

        def print_builder(args, zine_path, staging, data):
            if build_error == "print":
                raise ReleaseError("print failed")
            directory = staging / "print"
            directory.mkdir()
            (directory / "publication-print.html").write_text("print", encoding="utf-8")
            return {"status": "REVIEW_ARTIFACTS_BUILT", "mode": args.mode}

        def regressions():
            if regression_error:
                raise ReleaseError(regression_error)
            return ["test-example.py"]

        return (
            mock.patch.object(release_module, "validate_zine", return_value=0),
            mock.patch.object(
                release_module, "validate_asset_integrity", return_value=asset_report
            ),
            mock.patch.object(release_module, "run_regressions", side_effect=regressions),
            mock.patch.object(
                release_module, "build_preview_artifact", side_effect=preview_builder
            ),
            mock.patch.object(
                release_module, "build_studio_artifact", side_effect=studio_builder
            ),
            mock.patch.object(
                release_module, "build_print_artifacts", side_effect=print_builder
            ),
            mock.patch.object(
                release_module,
                "generator_evidence",
                return_value=[
                    {"path": path, "sha256": "test-sha256"}
                    for path in release_module.GENERATOR_FILES
                ],
            ),
        )

    def run_with_patches(self, args, **options):
        patches = self.patches(**options)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
        ):
            return release(args)

    def test_review_release_is_atomic_and_records_evidence(self):
        source_before = hashlib.sha256(self.zine.read_bytes()).hexdigest()
        result = self.run_with_patches(release_args(self.zine, self.output))
        source_after = hashlib.sha256(self.zine.read_bytes()).hexdigest()
        self.assertEqual(result, self.output)
        self.assertEqual(source_before, source_after)
        self.assertTrue((self.output / "preview.html").is_file())
        self.assertTrue((self.output / "studio.html").is_file())
        report = json.loads(
            (self.output / "release-report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["format"], "zineos-release-report")
        self.assertEqual(report["projectId"], "test-zine")
        self.assertEqual(report["validation"]["schema"], "PASS")
        self.assertEqual(report["validation"]["assets"]["status"], "PASS")
        self.assertEqual(
            report["validation"]["assets"]["zine"],
            "projects/test-zine/zine.yaml",
        )
        self.assertEqual(report["validation"]["regressions"]["status"], "PASS")
        self.assertIn(
            report["git"]["workingTree"], {"CLEAN", "DIRTY", "UNAVAILABLE"}
        )
        self.assertEqual(
            {item["path"] for item in report["generators"]},
            set(release_module.GENERATOR_FILES),
        )
        self.assertEqual(
            {artifact["path"] for artifact in report["artifacts"]},
            {"preview.html", "studio.html", "print/publication-print.html"},
        )
        self.assertFalse(any(self.output.parent.glob(".test-release-*")))

    def test_existing_or_external_output_is_rejected(self):
        self.output.mkdir(parents=True)
        with self.assertRaisesRegex(ReleaseError, "refusing to overwrite"):
            safe_release_output(self.output, "test-zine", "review")
        with self.assertRaisesRegex(ReleaseError, "must stay under"):
            safe_release_output(self.root / "outside", "test-zine", "review")

    def test_asset_failure_stops_before_artifact_creation(self):
        with self.assertRaisesRegex(ReleaseError, "asset integrity failed"):
            self.run_with_patches(
                release_args(self.zine, self.output), asset_status="FAIL"
            )
        self.assertFalse(self.output.exists())

    def test_regression_failure_stops_before_staging(self):
        with self.assertRaisesRegex(ReleaseError, "regression failed"):
            self.run_with_patches(
                release_args(self.zine, self.output),
                regression_error="regression failed",
            )
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / "output" / "releases").exists())

    def test_unsupported_print_configuration_stops_before_regressions(self):
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        data["output"]["page_size"] = "Letter"
        self.zine.write_text(
            yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
        )
        with mock.patch.object(release_module, "validate_zine", return_value=0), mock.patch.object(
            release_module,
            "validate_asset_integrity",
            return_value={
                "status": "PASS", "zine": str(self.zine), "assets": 0,
                "references": 0, "errors": [], "warnings": [],
            },
        ), mock.patch.object(release_module, "run_regressions") as regressions:
            with self.assertRaisesRegex(ReleaseError, "output.page_size"):
                release(release_args(self.zine, self.output))
            regressions.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_build_failure_removes_partial_staging(self):
        with self.assertRaisesRegex(ReleaseError, "studio failed"):
            self.run_with_patches(
                release_args(self.zine, self.output), build_error="studio"
            )
        self.assertFalse(self.output.exists())
        self.assertFalse(any(self.output.parent.glob(".test-release-*")))

    def test_print_mode_requires_profile_before_regressions(self):
        args = release_args(self.zine, self.output, mode="print")
        with mock.patch.object(release_module, "validate_zine", return_value=0), mock.patch.object(
            release_module,
            "validate_asset_integrity",
            return_value={
                "status": "PASS", "zine": str(self.zine), "assets": 0,
                "references": 0, "errors": [], "warnings": [],
            },
        ), mock.patch.object(release_module, "run_regressions") as regressions:
            with self.assertRaisesRegex(ReleaseError, "requires --icc-profile"):
                release(args)
            regressions.assert_not_called()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

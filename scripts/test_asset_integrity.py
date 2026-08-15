#!/usr/bin/env python3

import base64
from pathlib import Path
import tempfile
import unittest

import yaml

from validate_assets import validate_asset_integrity


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAADUlEQVR42mNk+M/wHwAF"
    "gAJ/l1jK8QAAAABJRU5ErkJggg=="
)


class AssetIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zineos-assets-test-")
        self.root = Path(self.temporary.name)
        (self.root / "assets").mkdir()
        (self.root / "assets" / "photo.PNG").write_bytes(PNG)

    def tearDown(self):
        self.temporary.cleanup()

    def write_zine(self, assets=None, block=None, settings=None):
        data = {
            "assets": assets if assets is not None else [
                {"id": "photo-001", "type": "image", "source": "assets/photo.PNG"}
            ],
            "pages": [{
                "id": "page-001",
                "pages": [1],
                "blocks": [block or {"id": "block-001", "type": "PHOTO", "asset": "photo-001"}],
                "layout": {"type": "minimal", "settings": settings or {}},
            }],
        }
        path = self.root / "zine.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        return path

    def test_valid_referenced_asset_passes(self):
        report = validate_asset_integrity(self.write_zine())
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["assets"], 1)
        self.assertEqual(report["references"], 1)
        self.assertEqual(report["warnings"], [])

    def test_missing_file_is_blocking(self):
        path = self.write_zine()
        (self.root / "assets" / "photo.PNG").unlink()
        report = validate_asset_integrity(path)
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("missing" in error for error in report["errors"]))

    def test_filename_case_mismatch_is_blocking(self):
        assets = [{"id": "photo-001", "type": "image", "source": "assets/PHOTO.png"}]
        report = validate_asset_integrity(self.write_zine(assets=assets))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("case mismatch" in error for error in report["errors"]))

    def test_extension_content_mismatch_is_blocking(self):
        assets = [{"id": "photo-001", "type": "image", "source": "assets/photo.jpg"}]
        (self.root / "assets" / "photo.jpg").write_bytes(PNG)
        report = validate_asset_integrity(self.write_zine(assets=assets))
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("extension expects JPEG" in error for error in report["errors"]))

    def test_unsafe_path_and_unknown_reference_are_blocking(self):
        assets = [{"id": "photo-001", "type": "image", "source": "../private.png"}]
        settings = {"assets": ["unknown-photo"]}
        report = validate_asset_integrity(
            self.write_zine(assets=assets, settings=settings)
        )
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any("unsafe" in error for error in report["errors"]))
        self.assertTrue(any("unknown asset reference" in error for error in report["errors"]))

    def test_layout_assets_are_references_and_unused_assets_are_warnings(self):
        assets = [
            {"id": "photo-001", "type": "image", "source": "assets/photo.PNG"},
            {"id": "unused-001", "type": "image", "source": "assets/photo.PNG"},
        ]
        block = {"id": "block-001", "type": "TEXT", "content": ""}
        settings = {"layers": [{"background_asset": "photo-001"}]}
        report = validate_asset_integrity(
            self.write_zine(assets=assets, block=block, settings=settings)
        )
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["references"], 1)
        self.assertEqual(report["warnings"], ["Unused asset is retained: unused-001"])

    def test_missing_unused_asset_warns_without_blocking_release(self):
        assets = [
            {"id": "photo-001", "type": "image", "source": "assets/photo.PNG"},
            {"id": "old-cover", "type": "image", "source": "assets/missing.jpg"},
        ]
        report = validate_asset_integrity(self.write_zine(assets=assets))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(any("Unused asset issue" in item for item in report["warnings"]))
        self.assertFalse(report["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

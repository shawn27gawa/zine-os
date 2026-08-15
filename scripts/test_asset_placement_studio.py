#!/usr/bin/env python3

import base64
import copy
import hashlib
import re
import tempfile
import unittest
from pathlib import Path

from build_asset_studio import build_studio_config, build_studio_html
from build_preview import load_yaml
from validate_asset_placement import validate_manifest_data


ROOT = Path(__file__).resolve().parents[1]
ZINE_PATH = ROOT / "examples" / "ZINE_001" / "zine.yaml"


def valid_settings():
    return {
        "fit": "cover",
        "x": 50,
        "y": 50,
        "scale": 1,
        "frameX": 50,
        "frameY": 50,
        "frameSize": 30,
    }


def valid_manifest():
    return {
        "format": "zineos-asset-placement",
        "version": 1,
        "projectId": "zine-001-our-memory",
        "zinePath": "examples/ZINE_001/zine.yaml",
        "sourceReference": {
            "gitCommit": "e7a54ff8c886d83051fa37d9ce2c36d6d47ba78e",
            "zineSha256": "a" * 64,
        },
        "placements": [
            {
                "key": "page-008:virtual:secondary-image",
                "pageUnitId": "page-008",
                "pages": [8],
                "kind": "free-layer",
                "blockId": None,
                "assetId": None,
                "assetIndex": None,
                "cellIndex": None,
                "role": "secondary-image",
                "monochrome": False,
                "source": {
                    "name": "P08_APEROL_GLASS_01.jpeg",
                    "type": "image/jpeg",
                    "size": 12345,
                    "lastModified": 0,
                },
                "previewDataUrl": None,
                "settings": {
                    "desktop": valid_settings(),
                    "mobile": valid_settings(),
                },
            }
        ],
    }


class AssetPlacementStudioTests(unittest.TestCase):
    def setUp(self):
        self.zine_data = load_yaml(ZINE_PATH)

    def test_config_exposes_current_assets_and_memory_cells_without_duplicates(self):
        config = build_studio_config(self.zine_data, ZINE_PATH)
        slots = [
            slot
            for page_unit in config["pageUnits"]
            for slot in page_unit["slots"]
        ]

        memory_slots = [slot for slot in slots if slot["kind"] == "memory-cell"]
        free_layers = [slot for slot in slots if slot["kind"] == "free-layer"]
        asset_keys = {slot["key"] for slot in slots if slot["kind"] == "asset"}

        self.assertEqual(len(memory_slots), 60)
        self.assertTrue(all(slot["monochrome"] for slot in memory_slots))
        self.assertEqual(memory_slots[0]["assetId"], "memory-001")
        self.assertEqual(memory_slots[30]["assetId"], "memory-001")
        self.assertEqual(free_layers, [])
        self.assertIn("spread-004-005:block-003:photo-001", asset_keys)
        self.assertIn("spread-020-021:block-023:photo-016", asset_keys)
        self.assertIn("page-010:block-033:glass-001", asset_keys)
        p67_slot = next(
            slot
            for slot in slots
            if slot["key"] == "spread-008-009:block-007:photo-006"
        )
        self.assertEqual(p67_slot["defaultPosition"], "center 70%")
        self.assertEqual(
            config["sourceReference"]["zineSha256"],
            hashlib.sha256(ZINE_PATH.read_bytes()).hexdigest(),
        )

    def test_studio_build_does_not_mutate_publication_data(self):
        original = copy.deepcopy(self.zine_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "ZINE_001_STUDIO.html"
            generated = build_studio_html(self.zine_data, ZINE_PATH, output_path)

        self.assertEqual(self.zine_data, original)
        self.assertIn("ZineOS Asset Placement Studio", generated)
        self.assertIn("Export manifest", generated)
        self.assertIn("Choose image(s)", generated)
        self.assertIn("Download JSON", generated)
        self.assertIn("Copy JSON", generated)
        self.assertNotIn('src="studio/asset-placement.js"', generated)

    def test_embedded_preview_assets_resolve_from_studio_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "ZINE_001_STUDIO.html"
            generated = build_studio_html(self.zine_data, ZINE_PATH, output_path)
            payload_match = re.search(
                r'<script id="preview-source"[^>]*>([^<]+)</script>',
                generated,
            )
            self.assertIsNotNone(payload_match)
            preview_html = base64.b64decode(payload_match.group(1)).decode("utf-8")
            source_match = re.search(
                r'<img src="([^"]*photo-006\.jpeg)"',
                preview_html,
            )
            self.assertIsNotNone(source_match)
            resolved = (output_path.parent.resolve() / source_match.group(1)).resolve()
            self.assertEqual(
                resolved,
                (ROOT / "examples" / "ZINE_001" / "assets" / "photo-006.jpeg").resolve(),
            )
            self.assertTrue(resolved.is_file())

    def test_manifest_validator_accepts_supported_manifest(self):
        self.assertEqual(validate_manifest_data(valid_manifest()), [])

    def test_manifest_validator_rejects_paths_and_out_of_range_values(self):
        manifest = valid_manifest()
        placement = manifest["placements"][0]
        placement["source"]["name"] = "../private.jpg"
        placement["settings"]["desktop"]["x"] = 140

        errors = validate_manifest_data(manifest)

        self.assertTrue(any("must not contain a path" in error for error in errors))
        self.assertTrue(any("must be between 0 and 100" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3

import hashlib
import json
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

from build_preview import build_html
from validate_asset_placement import validate_manifest_data as validate_asset
from validate_text_placement import validate_manifest_data as validate_text
from validate_zine import validate_zine


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZINE = ROOT / "examples" / "ZINE_001" / "zine.yaml"
APPLY_SCRIPT = ROOT / "scripts" / "apply_manifest.py"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settings(fit="cover", x=50, y=50, scale=1):
    return {
        "fit": fit,
        "x": x,
        "y": y,
        "scale": scale,
        "frameX": 50,
        "frameY": 50,
        "frameSize": 30,
    }


class ManifestApplicationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(
            prefix="manifest-test-", dir=ROOT / "tmp"
        )
        self.root = Path(self.temporary.name)
        self.publication = self.root / "publication"
        self.publication.mkdir()
        self.zine = self.publication / "zine.yaml"
        self.zine.write_bytes(SOURCE_ZINE.read_bytes())
        self.inbox = self.root / "inbox"
        self.inbox.mkdir()
        self.image = self.inbox / "NEW_IMAGE.JPG"
        self.image.write_bytes(b"creator image bytes")

    def tearDown(self):
        self.temporary.cleanup()

    def reference(self):
        return {"gitCommit": "test", "zineSha256": digest(self.zine)}

    def relative_zine(self):
        return str(self.zine.relative_to(ROOT))

    def asset_manifest(self):
        return {
            "format": "zineos-asset-placement",
            "version": 1,
            "projectId": "zine-001-our-memory",
            "zinePath": self.relative_zine(),
            "sourceReference": self.reference(),
            "placements": [
                {
                    "key": "page-010:block-008:bottle-001",
                    "pageUnitId": "page-010",
                    "pages": [10],
                    "kind": "asset",
                    "blockId": "block-008",
                    "assetId": "bottle-001",
                    "assetIndex": 0,
                    "cellIndex": None,
                    "role": None,
                    "monochrome": False,
                    "source": {
                        "name": self.image.name,
                        "type": "image/jpeg",
                        "size": self.image.stat().st_size,
                        "lastModified": 0,
                    },
                    "previewDataUrl": None,
                    "settings": {
                        "desktop": settings(x=35, y=70, scale=1.2),
                        "mobile": settings(fit="contain", x=45, y=60),
                    },
                }
            ],
        }

    def text_manifest(self):
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in data["pages"] if page["id"] == "page-013")
        block = next(block for block in page["blocks"] if block["id"] == "block-013")
        return {
            "format": "zineos-text-placement",
            "version": 1,
            "projectId": "zine-001-our-memory",
            "zinePath": self.relative_zine(),
            "sourceReference": self.reference(),
            "edits": [
                {
                    "key": "page-013:block-013:text",
                    "pageUnitId": "page-013",
                    "blockId": "block-013",
                    "originalText": block["content"],
                    "text": "MÜNCHEN\n\nCreator-approved revised text.\n",
                    "typography": {
                        "font_size_px": 14,
                        "line_height": 1.8,
                        "width_percent": 80,
                        "x_mm": 2,
                        "y_mm": 3,
                        "columns": 1,
                        "rule_spacing_mm": None,
                    },
                }
            ],
        }

    def write_manifest(self, data, name="manifest.json"):
        path = self.root / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def run_apply(self, manifest, apply=False, asset_dir=None):
        command = [sys.executable, str(APPLY_SCRIPT), str(manifest)]
        if asset_dir:
            command.extend(["--asset-dir", str(asset_dir)])
        if apply:
            command.append("--apply")
        return subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
        )

    def test_asset_dry_run_is_non_writing_and_reports_narrow_change(self):
        before = self.zine.read_bytes()
        result = self.run_apply(
            self.write_manifest(self.asset_manifest()), asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("DRY RUN PASS", result.stdout)
        self.assertIn("COPY:", result.stdout)
        self.assertIn("block-008", result.stdout)
        self.assertEqual(self.zine.read_bytes(), before)
        self.assertFalse((self.publication / "assets" / self.image.name).exists())

    def test_asset_apply_copies_without_overwrite_and_updates_target(self):
        result = self.run_apply(
            self.write_manifest(self.asset_manifest()),
            apply=True,
            asset_dir=self.inbox,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(self.image.read_bytes(), b"creator image bytes")
        copied = self.publication / "assets" / self.image.name
        self.assertEqual(copied.read_bytes(), self.image.read_bytes())
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in data["pages"] if page["id"] == "page-010")
        block = next(block for block in page["blocks"] if block["id"] == "block-008")
        self.assertTrue(block["asset"].startswith("studio-new-image"))
        placement = block["metadata"]["zineos_studio"]["asset_placements"][
            block["asset"]
        ]
        self.assertEqual(placement["desktop"]["y"], 70)
        self.assertIn('project:\n  id: "zine-001-our-memory"', self.zine.read_text())
        self.assertEqual(validate_zine(self.zine), 0)

        rendered = build_html(data, self.zine, self.root / "preview.html")
        self.assertIn("data-studio-placement", rendered)
        self.assertIn("--studio-position: 35% 70%", rendered)

    def test_source_hash_mismatch_is_blocking(self):
        manifest = self.asset_manifest()
        manifest["sourceReference"]["zineSha256"] = "0" * 64
        before = self.zine.read_bytes()
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Publication source changed since export", result.stdout)
        self.assertEqual(self.zine.read_bytes(), before)

    def test_filename_case_mismatch_is_blocking(self):
        manifest = self.asset_manifest()
        manifest["placements"][0]["source"]["name"] = "new_image.jpg"
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact filename case", result.stdout)
        self.assertFalse((self.publication / "assets").exists())

    def test_source_size_mismatch_is_blocking(self):
        manifest = self.asset_manifest()
        manifest["placements"][0]["source"]["size"] += 1
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Source asset size changed since export", result.stdout)
        self.assertFalse((self.publication / "assets").exists())

    def test_memory_cell_apply_updates_only_selected_cell(self):
        manifest = self.asset_manifest()
        manifest["placements"][0].update({
            "key": "page-001:memory-cell:0",
            "pageUnitId": "page-001",
            "pages": [1],
            "kind": "memory-cell",
            "blockId": None,
            "assetId": "memory-001",
            "assetIndex": None,
            "cellIndex": 0,
            "monochrome": True,
        })
        before = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        after = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        before_page = next(page for page in before["pages"] if page["id"] == "page-001")
        after_page = next(page for page in after["pages"] if page["id"] == "page-001")
        self.assertNotEqual(
            before_page["layout"]["settings"]["assets"][0],
            after_page["layout"]["settings"]["assets"][0],
        )
        self.assertEqual(
            before_page["layout"]["settings"]["assets"][1:],
            after_page["layout"]["settings"]["assets"][1:],
        )
        self.assertIn("asset_placements", after_page["layout"]["settings"])

    def test_stale_asset_reference_is_blocking(self):
        manifest = self.asset_manifest()
        manifest["placements"][0]["assetId"] = "photo-999"
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Block asset reference changed since export", result.stdout)
        self.assertFalse((self.publication / "assets").exists())

    def test_gallery_edits_preserve_each_placement_and_copy_source_once(self):
        manifest = self.asset_manifest()
        first = manifest["placements"][0]
        first.update({
            "key": "spread-006-007:block-006:photo-002",
            "pageUnitId": "spread-006-007",
            "pages": [6, 7],
            "blockId": "block-006",
            "assetId": "photo-002",
            "assetIndex": 0,
        })
        second = deepcopy(first)
        second.update({
            "key": "spread-006-007:block-006:photo-003",
            "assetId": "photo-003",
            "assetIndex": 1,
            "settings": {
                "desktop": settings(x=65, y=25),
                "mobile": settings(x=60, y=30),
            },
        })
        manifest["placements"].append(second)
        result = self.run_apply(
            self.write_manifest(manifest), apply=True, asset_dir=self.inbox
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(result.stdout.count("COPY:"), 1)
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(p for p in data["pages"] if p["id"] == "spread-006-007")
        block = next(b for b in page["blocks"] if b["id"] == "block-006")
        self.assertNotEqual(block["assets"][0], block["assets"][1])
        placements = block["metadata"]["zineos_studio"]["asset_placements"]
        self.assertEqual(placements[block["assets"][0]]["desktop"]["x"], 35)
        self.assertEqual(placements[block["assets"][1]]["desktop"]["x"], 65)

    def test_duplicate_targets_are_rejected(self):
        asset_manifest = self.asset_manifest()
        duplicate = dict(asset_manifest["placements"][0])
        duplicate["key"] = "different-key"
        asset_manifest["placements"].append(duplicate)
        self.assertTrue(
            any("duplicates target" in error for error in validate_asset(asset_manifest))
        )

        text_manifest = self.text_manifest()
        duplicate_edit = dict(text_manifest["edits"][0])
        duplicate_edit["key"] = "different-key"
        text_manifest["edits"].append(duplicate_edit)
        self.assertTrue(
            any("duplicates target" in error for error in validate_text(text_manifest))
        )

    def test_text_apply_requires_original_and_renders_typography(self):
        manifest = self.text_manifest()
        self.assertEqual(validate_text(manifest), [])
        result = self.run_apply(self.write_manifest(manifest), apply=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in data["pages"] if page["id"] == "page-013")
        block = next(block for block in page["blocks"] if block["id"] == "block-013")
        self.assertEqual(block["content"], manifest["edits"][0]["text"])
        self.assertEqual(
            block["metadata"]["zineos_studio"]["text_placements"]["content"]["font_size_px"],
            14,
        )
        self.assertEqual(validate_zine(self.zine), 0)
        rendered = build_html(data, self.zine, self.root / "preview.html")
        self.assertIn("data-studio-text-placement", rendered)
        self.assertIn("--studio-text-font-size: 14px", rendered)

    def test_checklist_title_and_item_apply_as_distinct_stable_fields(self):
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in data["pages"] if page["id"] == "spread-024-025")
        block = next(block for block in page["blocks"] if block["id"] == "block-027")
        manifest = self.text_manifest()
        manifest["edits"] = [
            {
                "key": "spread-024-025:block-027:text:title",
                "pageUnitId": "spread-024-025",
                "blockId": "block-027",
                "field": "title",
                "originalText": block["title"],
                "text": "THINGS WE WILL DO",
                "typography": None,
            },
            {
                "key": "spread-024-025:block-027:text:items[0].text",
                "pageUnitId": "spread-024-025",
                "blockId": "block-027",
                "field": "items[0].text",
                "originalText": block["items"][0]["text"],
                "text": "ふたりで、もっといろいろな景色を見る。",
                "typography": {
                    "font_size_px": 16,
                    "line_height": 1.5,
                    "width_percent": 100,
                    "x_mm": 0,
                    "y_mm": 0,
                    "columns": 1,
                    "rule_spacing_mm": None,
                },
            },
        ]
        self.assertEqual(validate_text(manifest), [])
        result = self.run_apply(self.write_manifest(manifest), apply=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        updated = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in updated["pages"] if page["id"] == "spread-024-025")
        block = next(block for block in page["blocks"] if block["id"] == "block-027")
        self.assertEqual(block["title"], "THINGS WE WILL DO")
        self.assertEqual(block["items"][0]["text"], "ふたりで、もっといろいろな景色を見る。")
        self.assertIn(
            "items[0].text",
            block["metadata"]["zineos_studio"]["text_placements"],
        )
        self.assertEqual(validate_zine(self.zine), 0)

    def test_original_text_mismatch_is_blocking(self):
        manifest = self.text_manifest()
        manifest["edits"][0]["originalText"] = "stale text"
        result = self.run_apply(self.write_manifest(manifest), apply=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Original text mismatch", result.stdout)

    def test_text_without_typography_preserves_exact_chomping(self):
        manifest = self.text_manifest()
        manifest["edits"][0]["text"] = "No trailing newline"
        manifest["edits"][0]["typography"] = None
        result = self.run_apply(self.write_manifest(manifest), apply=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        page = next(page for page in data["pages"] if page["id"] == "page-013")
        block = next(block for block in page["blocks"] if block["id"] == "block-013")
        self.assertEqual(block["content"], "No trailing newline")
        self.assertNotIn("metadata", block)

    def test_text_validator_reports_unknown_typography_without_crashing(self):
        manifest = self.text_manifest()
        manifest["edits"][0]["typography"]["unsupported"] = 1
        errors = validate_text(manifest)
        self.assertTrue(any("unsupported fields" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)

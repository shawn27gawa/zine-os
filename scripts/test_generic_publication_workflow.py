#!/usr/bin/env python3

"""Exercise the complete ZineOS workflow without relying on ZINE_001."""

import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import unquote, urlparse

import yaml

from bootstrap_project import bootstrap_project
from build_asset_studio import build_studio_config, build_studio_html, default_studio_output
from build_preview import build_html, default_preview_output, load_yaml
import release_zine as release_module
from validate_assets import validate_asset_integrity
from validate_zine import validate_zine


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "basic" / "zine.yaml"
APPLY_SCRIPT = ROOT / "scripts" / "apply_manifest.py"
PNG_LANDSCAPE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAADUlEQVR42mNk+M/wHwAF"
    "gAJ/l1jK8QAAAABJRU5ErkJggg=="
)
PNG_PORTRAIT = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAADUlEQVR42mNkYPj/HwAD"
    "AgH/5ncLrgAAAABJRU5ErkJggg=="
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def placement_settings(x=50, y=50):
    mode = {
        "fit": "cover",
        "x": x,
        "y": y,
        "scale": 1,
        "frameX": 50,
        "frameY": 50,
        "frameSize": 30,
    }
    return {"desktop": mode, "mobile": dict(mode)}


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            source = dict(attrs).get("src")
            if source:
                self.sources.append(source)


def assert_local_images_resolve(testcase, html_path):
    parser = ImageSources()
    parser.feed(html_path.read_text(encoding="utf-8"))
    testcase.assertTrue(parser.sources, f"No images found in {html_path}")
    for source in parser.sources:
        parsed = urlparse(source)
        testcase.assertIn(parsed.scheme, {"", "file"})
        if parsed.scheme == "file":
            target = Path(unquote(parsed.path))
        else:
            target = (html_path.parent / unquote(parsed.path)).resolve()
        testcase.assertTrue(target.is_file(), f"Broken image reference: {source}")


class GenericPublicationWorkflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "projects").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(
            prefix=".generic-workflow-", dir=ROOT / "projects"
        )
        self.root = Path(self.temporary.name)
        self.inbox = self.root / "GENERIC_PHOTO_INBOX"
        self.inbox.mkdir()
        (self.inbox / "PRIMARY.png").write_bytes(PNG_LANDSCAPE)
        (self.inbox / "REPLACEMENT.png").write_bytes(PNG_PORTRAIT)
        self.project = self.root / "field-notes"
        self.zine = self.project / "zine.yaml"

    def tearDown(self):
        self.temporary.cleanup()

    def bootstrap(self):
        args = argparse.Namespace(
            project_id="field-notes-002",
            title="Field Notes",
            inbox=self.inbox,
            output=self.project,
            language="en",
            creator="Example Creator",
            template=TEMPLATE,
            top_level_only=False,
            dry_run=False,
        )
        bootstrap_project(args)

    def add_creator_approved_structure(self):
        data = yaml.safe_load(self.zine.read_text(encoding="utf-8"))
        shutil.copy2(self.inbox / "PRIMARY.png", self.project / "assets" / "PRIMARY.png")
        data["project"]["description"] = "A generic publication workflow fixture."
        data["project"]["status"] = "editing"
        data["assets"] = [
            {"id": "photo-primary", "type": "image", "source": "assets/PRIMARY.png"}
        ]
        data["pages"][0]["blocks"] = [
            {"id": "block-photo", "type": "PHOTO", "asset": "photo-primary"}
        ]
        data["pages"][0]["layout"] = {"type": "full-page"}
        data["pages"][1]["blocks"] = [
            {"id": "block-text", "type": "TEXT", "content": "Draft field note."}
        ]
        data["output"]["color_mode"] = "CMYK"
        self.zine.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8"
        )

    def run_apply(self, manifest_path, *, asset_dir=None, apply=False):
        command = [sys.executable, str(APPLY_SCRIPT), str(manifest_path)]
        if asset_dir is not None:
            command.extend(["--asset-dir", str(asset_dir)])
        if apply:
            command.append("--apply")
        return subprocess.run(
            command, cwd=ROOT, check=False, capture_output=True, text=True
        )

    def asset_manifest(self):
        replacement = self.inbox / "REPLACEMENT.png"
        return {
            "format": "zineos-asset-placement",
            "version": 1,
            "projectId": "field-notes-002",
            "zinePath": self.zine.relative_to(ROOT).as_posix(),
            "sourceReference": {"gitCommit": "generic-test", "zineSha256": digest(self.zine)},
            "placements": [
                {
                    "key": "page-001:block-photo:photo-primary",
                    "pageUnitId": "page-001",
                    "pages": [1],
                    "kind": "asset",
                    "blockId": "block-photo",
                    "assetId": "photo-primary",
                    "assetIndex": 0,
                    "cellIndex": None,
                    "role": None,
                    "monochrome": False,
                    "source": {
                        "name": replacement.name,
                        "type": "image/png",
                        "size": replacement.stat().st_size,
                        "lastModified": 0,
                    },
                    "previewDataUrl": None,
                    "settings": placement_settings(x=42, y=61),
                }
            ],
        }

    def text_manifest(self):
        return {
            "format": "zineos-text-placement",
            "version": 1,
            "projectId": "field-notes-002",
            "zinePath": self.zine.relative_to(ROOT).as_posix(),
            "sourceReference": {"gitCommit": "generic-test", "zineSha256": digest(self.zine)},
            "edits": [
                {
                    "key": "spread-002-003:block-text:content",
                    "pageUnitId": "spread-002-003",
                    "blockId": "block-text",
                    "field": "content",
                    "originalText": "Draft field note.",
                    "text": "Creator-approved field note.",
                    "typography": None,
                }
            ],
        }

    def test_non_zine001_end_to_end_workflow(self):
        inbox_before = {path.name: digest(path) for path in self.inbox.iterdir()}
        self.bootstrap()

        inventory = json.loads(
            (self.project / "inbox.inventory.json").read_text(encoding="utf-8")
        )
        self.assertEqual(inventory["projectId"], "field-notes-002")
        self.assertEqual(inventory["candidateCount"], 2)
        self.assertTrue(
            all(item["selectionStatus"] == "unassigned" for item in inventory["candidates"])
        )
        self.assertEqual(inbox_before, {path.name: digest(path) for path in self.inbox.iterdir()})

        self.add_creator_approved_structure()
        self.assertEqual(validate_zine(self.zine), 0)
        self.assertEqual(validate_asset_integrity(self.zine)["status"], "PASS")

        before_dry_run = digest(self.zine)
        asset_manifest_path = self.root / "asset-manifest.json"
        asset_manifest_path.write_text(
            json.dumps(self.asset_manifest(), indent=2), encoding="utf-8"
        )
        dry_run = self.run_apply(asset_manifest_path, asset_dir=self.inbox)
        self.assertEqual(dry_run.returncode, 0, dry_run.stdout + dry_run.stderr)
        self.assertIn("DRY RUN PASS", dry_run.stdout)
        self.assertEqual(digest(self.zine), before_dry_run)
        applied = self.run_apply(asset_manifest_path, asset_dir=self.inbox, apply=True)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertIn("APPLY PASS", applied.stdout)

        text_manifest_path = self.root / "text-manifest.json"
        text_manifest_path.write_text(
            json.dumps(self.text_manifest(), indent=2), encoding="utf-8"
        )
        applied = self.run_apply(text_manifest_path, apply=True)
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        self.assertIn("APPLY PASS", applied.stdout)

        data = load_yaml(self.zine)
        self.assertEqual(default_preview_output(data).name, "FIELD_NOTES_002.html")
        self.assertEqual(default_studio_output(data).name, "FIELD_NOTES_002_STUDIO.html")
        self.assertEqual(validate_zine(self.zine), 0)
        self.assertEqual(validate_asset_integrity(self.zine)["status"], "PASS")
        self.assertEqual(
            data["pages"][1]["blocks"][0]["content"], "Creator-approved field note."
        )
        self.assertEqual(data["pages"][0]["blocks"][0]["asset"], "studio-replacement")
        data["pages"][0]["layout"] = {
            "type": "photo-rhythm-spread",
            "variant": "grid",
        }

        preview = self.root / "preview.html"
        studio = self.root / "studio.html"
        preview.write_text(build_html(data, self.zine, preview), encoding="utf-8")
        studio.write_text(build_studio_html(data, self.zine, studio), encoding="utf-8")
        assert_local_images_resolve(self, preview)
        self.assertIn(
            'class="page-body layout-photo-rhythm-spread variant-grid"',
            preview.read_text(encoding="utf-8"),
        )
        studio_config = build_studio_config(data, self.zine)
        self.assertEqual(studio_config["project"]["id"], "field-notes-002")
        self.assertEqual(
            studio_config["pageUnits"][0]["slots"][0]["assetId"],
            "studio-replacement",
        )
        self.assertIn("Field Notes — ZineOS Unified Studio", studio.read_text(encoding="utf-8"))
        self.assertNotIn("ZINE_001", preview.read_text(encoding="utf-8"))
        self.assertNotIn("ZINE_001", studio.read_text(encoding="utf-8"))

        release_module.RELEASE_ROOT = self.root / "releases"
        release_args = argparse.Namespace(
            zine=self.zine,
            mode="review",
            output=None,
            icc_profile=None,
            ghostscript=None,
            chrome=None,
        )
        with mock.patch.object(
            release_module, "run_regressions", return_value=["generic-publication-workflow"]
        ):
            release_path = release_module.release(release_args)
        report = json.loads(
            (release_path / "release-report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["projectId"], "field-notes-002")
        self.assertEqual(report["validation"]["schema"], "PASS")
        self.assertEqual(report["validation"]["assets"]["status"], "PASS")
        self.assertEqual(report["validation"]["print"]["status"], "REVIEW_ARTIFACTS_BUILT")
        assert_local_images_resolve(self, release_path / "preview.html")
        self.assertIn(
            "Field Notes — ZineOS Unified Studio",
            (release_path / "studio.html").read_text(encoding="utf-8"),
        )
        for artifact in release_path.rglob("*"):
            if artifact.is_file() and artifact.suffix in {".html", ".md", ".txt", ".json"}:
                self.assertNotIn("ZINE_001", artifact.read_text(encoding="utf-8"))

        self.assertEqual(inbox_before, {path.name: digest(path) for path in self.inbox.iterdir()})


if __name__ == "__main__":
    unittest.main(verbosity=2)

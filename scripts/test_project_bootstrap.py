#!/usr/bin/env python3

import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import unquote

import yaml

import bootstrap_project as bootstrap_module
from bootstrap_project import BootstrapError, bootstrap_project, inventory_inbox
import build_asset_studio as studio_module
from build_preview import load_yaml
from validate_zine import validate_zine


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "basic" / "zine.yaml"
PNG_LANDSCAPE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAADUlEQVR42mNk+M/wHwAF"
    "gAJ/l1jK8QAAAABJRU5ErkJggg=="
)
PNG_PORTRAIT = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAACCAYAAACZgbYnAAAADUlEQVR42mNkYPj/HwAD"
    "AgH/5ncLrgAAAABJRU5ErkJggg=="
)


def args_for(inbox, output, **overrides):
    values = {
        "project_id": "new-zine",
        "title": "New Zine",
        "inbox": inbox,
        "output": output,
        "language": "ja",
        "creator": "Creator",
        "template": TEMPLATE,
        "top_level_only": False,
        "dry_run": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ProjectBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zineos-bootstrap-test-")
        self.root = Path(self.temporary.name)
        self.original_root = bootstrap_module.ROOT
        self.original_projects_directory = bootstrap_module.DEFAULT_PROJECTS_DIRECTORY
        self.original_studio_root = studio_module.ROOT
        bootstrap_module.ROOT = self.root.resolve()
        bootstrap_module.DEFAULT_PROJECTS_DIRECTORY = self.root.resolve() / "projects"
        studio_module.ROOT = self.root.resolve()
        self.inbox = self.root / "PHOTO_INBOX"
        self.inbox.mkdir()
        (self.inbox / "ROME_01.PNG").write_bytes(PNG_LANDSCAPE)
        nested = self.inbox / "COVER_CANDIDATES"
        nested.mkdir()
        (nested / "PORTRAIT_01.png").write_bytes(PNG_PORTRAIT)
        (nested / "DUPLICATE.png").write_bytes(PNG_LANDSCAPE)
        (self.inbox / "notes.txt").write_text("not an image", encoding="utf-8")

    def tearDown(self):
        bootstrap_module.ROOT = self.original_root
        bootstrap_module.DEFAULT_PROJECTS_DIRECTORY = self.original_projects_directory
        studio_module.ROOT = self.original_studio_root
        self.temporary.cleanup()

    def test_inventory_is_factual_recursive_and_deterministic(self):
        candidates = inventory_inbox(self.inbox)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(
            [candidate["relativePath"] for candidate in candidates],
            [
                "COVER_CANDIDATES/DUPLICATE.png",
                "COVER_CANDIDATES/PORTRAIT_01.png",
                "ROME_01.PNG",
            ],
        )
        self.assertTrue(all(item["selectionStatus"] == "unassigned" for item in candidates))
        portrait = next(item for item in candidates if item["filename"] == "PORTRAIT_01.png")
        self.assertEqual((portrait["width"], portrait["height"]), (1, 2))
        self.assertEqual(portrait["orientation"], "portrait")
        self.assertEqual(portrait["format"], "PNG")
        self.assertTrue(portrait["extensionMatchesFormat"])
        duplicate = next(item for item in candidates if item["filename"] == "ROME_01.PNG")
        self.assertEqual(duplicate["duplicateOf"], "candidate-0001")

    def test_inventory_reports_extension_content_mismatch(self):
        mismatch_inbox = self.root / "MISMATCH_INBOX"
        mismatch_inbox.mkdir()
        (mismatch_inbox / "actually-png.jpg").write_bytes(PNG_LANDSCAPE)
        candidate = inventory_inbox(mismatch_inbox)[0]
        self.assertEqual(candidate["expectedFormat"], "JPEG")
        self.assertEqual(candidate["format"], "PNG")
        self.assertFalse(candidate["extensionMatchesFormat"])

    def test_bootstrap_creates_neutral_valid_project_without_touching_inbox(self):
        output = self.root / "projects" / "NEW_PROJECT"
        before = {
            path.relative_to(self.inbox): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.inbox.rglob("*") if path.is_file()
        }
        bootstrap_project(args_for(self.inbox, output))
        after = {
            path.relative_to(self.inbox): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.inbox.rglob("*") if path.is_file()
        }

        self.assertEqual(before, after)
        self.assertEqual(validate_zine(output / "zine.yaml"), 0)
        zine = yaml.safe_load((output / "zine.yaml").read_text(encoding="utf-8"))
        self.assertEqual(zine["project"]["id"], "new-zine")
        self.assertEqual(zine["project"]["title"], "New Zine")
        self.assertEqual(zine["assets"], [])
        self.assertEqual([page for unit in zine["pages"] for page in unit["pages"]], [1, 2, 3, 4])
        serialized = yaml.safe_dump(zine, allow_unicode=True)
        self.assertNotIn("EUROPE", serialized.upper())
        self.assertNotIn("ROMA", serialized.upper())

        inventory = json.loads((output / "inbox.inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(inventory["selectionStatus"], "creator-review-required")
        self.assertEqual(inventory["candidateCount"], 3)
        self.assertTrue(all(item["selectionStatus"] == "unassigned" for item in inventory["candidates"]))
        studio_config = studio_module.build_studio_config(
            load_yaml(output / "zine.yaml"), (output / "zine.yaml").resolve()
        )
        self.assertEqual(studio_config["zinePath"], "projects/NEW_PROJECT/zine.yaml")
        self.assertEqual(studio_config["project"]["id"], "new-zine")
        review = (output / "INBOX_REVIEW.html").read_text(encoding="utf-8")
        self.assertIn("ROME_01.PNG", review)
        self.assertIn("UNASSIGNED", review)
        self.assertIn("Nothing is selected", review)
        sources = re.findall(r'<img src="([^"]+)"', review)
        self.assertEqual(len(sources), 3)
        self.assertTrue(all(
            ((output / unquote(source)).resolve()).is_file()
            for source in sources
        ))

    def test_dry_run_does_not_create_output(self):
        output = self.root / "projects" / "DRY_RUN_PROJECT"
        result = bootstrap_project(args_for(self.inbox, output, dry_run=True))
        self.assertEqual(result[0], output.resolve())
        self.assertFalse(output.exists())

    def test_existing_output_and_invalid_id_are_rejected(self):
        output = self.root / "projects" / "EXISTING"
        output.parent.mkdir()
        output.mkdir()
        with self.assertRaisesRegex(BootstrapError, "refusing to overwrite"):
            bootstrap_project(args_for(self.inbox, output))
        with self.assertRaisesRegex(BootstrapError, "project ID"):
            bootstrap_project(
                args_for(self.inbox, self.root / "projects" / "OTHER", project_id="Bad Project")
            )

    def test_top_level_only_excludes_nested_candidates(self):
        output = self.root / "projects" / "TOP_LEVEL"
        _, candidates, _ = bootstrap_project(
            args_for(self.inbox, output, top_level_only=True, dry_run=True)
        )
        self.assertEqual([item["filename"] for item in candidates], ["ROME_01.PNG"])

    def test_output_outside_projects_is_rejected(self):
        with self.assertRaisesRegex(BootstrapError, "projects directory"):
            bootstrap_project(args_for(self.inbox, self.root / "OUTSIDE"))

    def test_output_inside_inbox_is_rejected(self):
        project_inbox = self.root / "projects" / "SOURCE_INBOX"
        project_inbox.mkdir(parents=True)
        with self.assertRaisesRegex(BootstrapError, "inside the photo inbox"):
            bootstrap_project(
                args_for(project_inbox, project_inbox / "generated-project")
            )

    def test_default_output_uses_project_id_under_projects(self):
        output, _, _ = bootstrap_project(
            args_for(self.inbox, None, project_id="default-place", dry_run=True)
        )
        self.assertEqual(output, self.root.resolve() / "projects" / "default-place")


if __name__ == "__main__":
    unittest.main(verbosity=2)

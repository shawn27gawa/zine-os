#!/usr/bin/env python3

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from build_preview import render_asset_visual, resolve_asset_path


ROOT = Path(__file__).resolve().parents[1]
ZINE_001_DIR = ROOT / "examples" / "ZINE_001"


class PreviewAssetPathTests(unittest.TestCase):
    def assert_reference_resolves(self, output_dir, reference, asset_path):
        resolved_reference = (output_dir.resolve() / reference).resolve()
        self.assertEqual(resolved_reference, asset_path.resolve())
        self.assertTrue(resolved_reference.is_file())

    def test_repository_preview_preserves_case_and_extension(self):
        assets = {
            "photo-006": {
                "id": "photo-006",
                "source": "assets/photo-006.jpeg",
            }
        }

        _, reference = resolve_asset_path(
            "photo-006",
            assets,
            ZINE_001_DIR,
            ROOT / "preview",
        )

        expected = os.path.join(
            "..",
            "examples",
            "ZINE_001",
            "assets",
            "photo-006.jpeg",
        )
        self.assertEqual(reference, expected)
        self.assert_reference_resolves(
            ROOT / "preview",
            reference,
            ZINE_001_DIR / "assets" / "photo-006.jpeg",
        )

    def test_ordinary_temporary_output_resolves_asset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zine_dir = root / "publication"
            output_dir = root / "output"
            asset_path = zine_dir / "assets" / "Photo.JPEG"
            asset_path.parent.mkdir(parents=True)
            output_dir.mkdir()
            asset_path.write_bytes(b"preview asset")

            assets = {
                "photo": {
                    "id": "photo",
                    "source": "assets/Photo.JPEG",
                }
            }
            _, reference = resolve_asset_path(
                "photo",
                assets,
                zine_dir,
                output_dir,
            )

            self.assertEqual(Path(reference).name, "Photo.JPEG")
            self.assert_reference_resolves(
                output_dir,
                reference,
                asset_path,
            )

    def test_symlinked_output_uses_resolved_artifact_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zine_dir = root / "publication"
            asset_path = zine_dir / "assets" / "photo.jpeg"
            actual_output = root / "physical" / "nested" / "preview"
            linked_output = root / "preview-link"

            asset_path.parent.mkdir(parents=True)
            actual_output.mkdir(parents=True)
            asset_path.write_bytes(b"preview asset")

            try:
                linked_output.symlink_to(actual_output, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Directory symlinks unavailable: {error}")

            assets = {
                "photo": {
                    "id": "photo",
                    "source": "assets/photo.jpeg",
                }
            }
            _, reference = resolve_asset_path(
                "photo",
                assets,
                zine_dir,
                linked_output,
            )

            self.assert_reference_resolves(
                linked_output,
                reference,
                asset_path,
            )

    def test_macos_tmp_alias_when_available(self):
        lexical_tmp = Path("/tmp")

        if lexical_tmp.resolve() == lexical_tmp.absolute():
            self.skipTest("/tmp is not a symlinked path in this environment")

        with tempfile.TemporaryDirectory(dir=lexical_tmp) as temp_dir:
            output_dir = Path(temp_dir)
            assets = {
                "photo-006": {
                    "id": "photo-006",
                    "source": "assets/photo-006.jpeg",
                }
            }
            _, reference = resolve_asset_path(
                "photo-006",
                assets,
                ZINE_001_DIR,
                output_dir,
            )

            self.assert_reference_resolves(
                output_dir,
                reference,
                ZINE_001_DIR / "assets" / "photo-006.jpeg",
            )

    def test_missing_asset_keeps_placeholder_behavior(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            zine_dir = root / "publication"
            output_dir = root / "preview"
            zine_dir.mkdir()
            output_dir.mkdir()
            assets = {
                "missing": {
                    "id": "missing",
                    "source": "assets/missing.jpg",
                    "title": "Missing image",
                }
            }

            asset, reference = resolve_asset_path(
                "missing",
                assets,
                zine_dir,
                output_dir,
            )
            rendered = render_asset_visual(
                "missing",
                assets,
                zine_dir,
                output_dir,
            )

            self.assertEqual(asset, assets["missing"])
            self.assertIsNone(reference)
            self.assertIn("asset-placeholder", rendered)
            self.assertNotIn("<img", rendered)

    def test_packaged_preview_remains_relocatable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            package = root / "package"
            zine_dir = package / "examples" / "ZINE_001"
            output_dir = package / "preview"
            asset_path = zine_dir / "assets" / "photo-006.jpeg"
            asset_path.parent.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            asset_path.write_bytes(b"preview asset")

            assets = {
                "photo-006": {
                    "id": "photo-006",
                    "source": "assets/photo-006.jpeg",
                }
            }
            _, reference = resolve_asset_path(
                "photo-006",
                assets,
                zine_dir,
                output_dir,
            )

            expected = os.path.join(
                "..",
                "examples",
                "ZINE_001",
                "assets",
                "photo-006.jpeg",
            )
            self.assertEqual(reference, expected)
            self.assert_reference_resolves(
                output_dir,
                reference,
                asset_path,
            )

            relocated = root / "relocated"
            shutil.copytree(package, relocated)
            relocated_reference = (
                relocated / "preview" / reference
            ).resolve()
            self.assertTrue(relocated_reference.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)

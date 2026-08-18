#!/usr/bin/env python3

"""Run the canonical repository validation sequence used by CI."""

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    ("setup", "scripts/check_setup.py"),
    ("basic template schema", "scripts/validate_zine.py", "templates/basic/zine.yaml"),
    ("ZINE_001 schema", "scripts/validate_zine.py", "examples/ZINE_001/zine.yaml"),
    ("ZINE_001 assets", "scripts/validate_assets.py", "examples/ZINE_001/zine.yaml"),
    (
        "ZINE_001 preview",
        "scripts/build_preview.py",
        "examples/ZINE_001/zine.yaml",
        "preview/ZINE_001.html",
    ),
    ("preview asset paths", "scripts/test_preview_asset_paths.py"),
    (
        "ZINE_001 Unified Studio",
        "scripts/build_asset_studio.py",
        "examples/ZINE_001/zine.yaml",
        "preview/ZINE_001_STUDIO.html",
    ),
    ("Unified Studio", "scripts/test_asset_placement_studio.py"),
    ("manifest application", "scripts/test_manifest_application.py"),
    ("project bootstrap", "scripts/test_project_bootstrap.py"),
    ("asset integrity", "scripts/test_asset_integrity.py"),
    ("standard print", "scripts/test_print_package.py"),
    ("one-command release", "scripts/test_release_zine.py"),
    ("generic publication workflow", "scripts/test_generic_publication_workflow.py"),
    ("documentation links", "scripts/test_documentation_links.py"),
)


def main():
    for label, *arguments in COMMANDS:
        print(f"VALIDATE START: {label}", flush=True)
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, check=False)
        if result.returncode != 0:
            print(f"VALIDATE FAIL: {label}", file=sys.stderr)
            return result.returncode
        print(f"VALIDATE PASS: {label}", flush=True)
    print("VALIDATE ZINEOS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

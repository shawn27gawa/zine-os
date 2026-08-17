#!/usr/bin/env python3

"""Check the local dependencies required for the repository workflow."""

import importlib
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = (
    ("yaml", "PyYAML"),
    ("jsonschema", "jsonschema"),
    ("referencing", "referencing"),
    ("pypdf", "pypdf"),
)


def main():
    errors = []
    if sys.version_info < (3, 10):
        errors.append(
            f"Python 3.10 or newer is required; found {sys.version.split()[0]}"
        )
    else:
        print(f"PYTHON PASS: {sys.version.split()[0]}")

    for module_name, package_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            errors.append(
                f"Missing Python package: {package_name} "
                f"(install with: {sys.executable} -m pip install -r requirements.txt)"
            )
        else:
            print(f"DEPENDENCY PASS: {package_name}")

    required_paths = (
        ROOT / "schema" / "zine.schema.json",
        ROOT / "schema" / "block.schema.json",
        ROOT / "templates" / "basic" / "zine.yaml",
    )
    for path in required_paths:
        if not path.is_file():
            errors.append(f"Required repository file is missing: {path.relative_to(ROOT)}")

    chrome = next(
        (
            executable
            for executable in ("google-chrome", "chromium", "chromium-browser")
            if shutil.which(executable)
        ),
        None,
    )
    if sys.platform == "darwin" and not chrome:
        application = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        chrome = str(application) if application.is_file() else None
    print(
        "OPTIONAL PRINT TOOL: Chrome/Chromium "
        + (f"available ({chrome})" if chrome else "not found")
    )
    ghostscript = shutil.which("gs")
    print(
        "OPTIONAL PRINT TOOL: Ghostscript "
        + (f"available ({ghostscript})" if ghostscript else "not found")
    )

    if errors:
        for error in errors:
            print(f"SETUP FAIL: {error}", file=sys.stderr)
        return 1
    print("SETUP PASS: core ZineOS validation and review tooling is available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

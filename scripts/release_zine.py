#!/usr/bin/env python3

"""Build a validated, immutable ZineOS review or print release."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

from build_asset_studio import build_studio_html
from build_preview import build_html, load_yaml
from build_print_package import (
    find_chrome,
    main as build_print_main,
    validate_icc_profile,
)
from validate_assets import print_report as print_asset_report
from validate_assets import validate_asset_integrity
from validate_zine import validate_zine


ROOT = Path(__file__).resolve().parents[1]
RELEASE_ROOT = ROOT / "output" / "releases"
REGRESSION_SCRIPTS = (
    "test_preview_asset_paths.py",
    "test_asset_placement_studio.py",
    "test_manifest_application.py",
    "test_project_bootstrap.py",
    "test_asset_integrity.py",
    "test_print_package.py",
)
GENERATOR_FILES = (
    "scripts/validate_zine.py",
    "scripts/validate_assets.py",
    "scripts/build_preview.py",
    "scripts/build_asset_studio.py",
    "scripts/build_print_package.py",
    "scripts/release_zine.py",
)


class ReleaseError(RuntimeError):
    """A release gate failed without changing publication source."""


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_evidence():
    commit_result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    changed_paths = []
    if status_result.returncode == 0:
        changed_paths = [
            line[3:] for line in status_result.stdout.splitlines() if len(line) > 3
        ]
    if status_result.returncode != 0:
        working_tree = "UNAVAILABLE"
    elif changed_paths:
        working_tree = "DIRTY"
    else:
        working_tree = "CLEAN"
    return {
        "commit": (
            commit_result.stdout.strip()
            if commit_result.returncode == 0 else None
        ),
        "workingTree": working_tree,
        "changedPaths": changed_paths,
    }


def generator_evidence():
    return [
        {
            "path": relative,
            "sha256": sha256_file(ROOT / relative),
        }
        for relative in GENERATOR_FILES
    ]


def resolve_repo_path(path):
    path = Path(path)
    return (path if path.is_absolute() else ROOT / path).resolve()


def safe_release_output(output, project_id, mode):
    release_root = RELEASE_ROOT.resolve()
    output_path = (
        resolve_repo_path(output)
        if output is not None
        else release_root / f"{project_id}-{mode}"
    ).resolve()
    try:
        relative = output_path.relative_to(release_root)
    except ValueError as error:
        raise ReleaseError(f"release output must stay under {release_root}") from error
    if not relative.parts:
        raise ReleaseError("release output must be a new directory below output/releases")
    if output_path.exists():
        raise ReleaseError(f"release output already exists; refusing to overwrite: {output_path}")
    return output_path


def run_regressions():
    passed = []
    for script_name in REGRESSION_SCRIPTS:
        script_path = ROOT / "scripts" / script_name
        print(f"REGRESSION START: {script_name}")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            raise ReleaseError(f"regression test failed: {script_name}")
        passed.append(script_name)
        print(f"REGRESSION PASS: {script_name}")
    return passed


def preflight_print(args, zine_data):
    if zine_data.get("output", {}).get("medium") != "print":
        raise ReleaseError("print mode requires publication output.medium: print")
    if args.icc_profile is None:
        raise ReleaseError("print mode requires --icc-profile")
    icc_profile = resolve_repo_path(args.icc_profile)
    if not icc_profile.is_file():
        raise ReleaseError(f"ICC profile not found: {icc_profile}")
    try:
        validate_icc_profile(icc_profile)
    except ValueError as error:
        raise ReleaseError(str(error)) from error

    chrome = find_chrome(args.chrome)
    if chrome is None:
        raise ReleaseError("Chrome or Chromium is required for print mode")
    if args.ghostscript:
        ghostscript = resolve_repo_path(args.ghostscript)
        if not ghostscript.is_file():
            raise ReleaseError(f"Ghostscript not found: {ghostscript}")
    else:
        discovered = shutil.which("gs")
        if not discovered:
            raise ReleaseError("Ghostscript is required for print mode")
        ghostscript = Path(discovered).resolve()
    return icc_profile, chrome, ghostscript


def build_preview_artifact(zine_data, zine_path, output_path):
    output_path.write_text(
        build_html(zine_data, zine_path, output_path), encoding="utf-8"
    )


def build_studio_artifact(zine_data, zine_path, output_path):
    output_path.write_text(
        build_studio_html(zine_data, zine_path, output_path), encoding="utf-8"
    )


def build_print_artifacts(args, zine_path, staging, zine_data):
    if zine_data.get("output", {}).get("medium") != "print":
        return {"status": "NOT_APPLICABLE", "mode": args.mode}

    print_directory = staging / "print"
    pdf_directory = staging / "pdf"
    print_directory.mkdir()
    pdf_directory.mkdir()
    command = [
        str(zine_path),
        str(print_directory / "publication-print.html"),
        "--pdf", str(pdf_directory / "rgb-proof.pdf"),
        "--cmyk-pdf", str(pdf_directory / "saddle-stitch-cmyk.pdf"),
        "--report", str(print_directory / "resolution-report.md"),
        "--spec", str(print_directory / "print-spec.txt"),
    ]
    if args.mode == "review":
        command.append("--html-only")
        status = "REVIEW_ARTIFACTS_BUILT"
    else:
        icc_profile, chrome, ghostscript = preflight_print(args, zine_data)
        command.extend([
            "--icc-profile", str(icc_profile),
            "--chrome", str(chrome),
            "--ghostscript", str(ghostscript),
        ])
        status = "CMYK_PRINT_BUILT"
    if build_print_main(command) != 0:
        raise ReleaseError("print build failed")
    return {"status": status, "mode": args.mode}


def artifact_inventory(staging):
    return [
        {
            "path": path.relative_to(staging).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(staging.rglob("*"))
        if path.is_file() and path.name != "release-report.json"
    ]


def build_release_report(args, zine_path, zine_data, asset_report, regressions, print_state, staging):
    portable_asset_report = {
        **asset_report,
        "zine": str(zine_path.relative_to(ROOT)),
    }
    return {
        "format": "zineos-release-report",
        "version": 1,
        "projectId": zine_data.get("project", {}).get("id"),
        "mode": args.mode,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "git": git_evidence(),
        "generators": generator_evidence(),
        "source": {
            "zinePath": str(zine_path.relative_to(ROOT)),
            "zineSha256": sha256_file(zine_path),
        },
        "validation": {
            "schema": "PASS",
            "assets": portable_asset_report,
            "regressions": {"status": "PASS", "scripts": regressions},
            "print": print_state,
        },
        "artifacts": artifact_inventory(staging),
    }


def release(args):
    zine_path = resolve_repo_path(args.zine)
    if not zine_path.is_file():
        raise ReleaseError(f"Zine file not found: {zine_path}")
    try:
        zine_path.relative_to(ROOT)
    except ValueError as error:
        raise ReleaseError("publication must be inside the ZineOS repository") from error

    if validate_zine(zine_path) != 0:
        raise ReleaseError("schema validation failed")
    zine_data = load_yaml(zine_path)
    project_id = zine_data.get("project", {}).get("id")
    if not isinstance(project_id, str) or not project_id:
        raise ReleaseError("publication project.id is required")

    asset_report = validate_asset_integrity(zine_path)
    print_asset_report(asset_report)
    if asset_report["status"] != "PASS":
        raise ReleaseError("asset integrity failed")

    if args.mode == "print":
        preflight_print(args, zine_data)

    output_path = safe_release_output(args.output, project_id, args.mode)
    regressions = run_regressions()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{output_path.name}-", dir=output_path.parent
    ))
    try:
        preview_path = staging / "preview.html"
        studio_path = staging / "studio.html"
        build_preview_artifact(zine_data, zine_path, preview_path)
        print(f"PREVIEW PASS: {preview_path}")
        build_studio_artifact(zine_data, zine_path, studio_path)
        print(f"STUDIO PASS: {studio_path}")
        print_state = build_print_artifacts(
            args, zine_path, staging, zine_data
        )
        report = build_release_report(
            args,
            zine_path,
            zine_data,
            asset_report,
            regressions,
            print_state,
            staging,
        )
        (staging / "release-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output_path)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    print(f"RELEASE PASS: {output_path}")
    return output_path


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate and build one immutable ZineOS release."
    )
    parser.add_argument("zine", type=Path)
    parser.add_argument("--mode", choices=("review", "print"), default="review")
    parser.add_argument(
        "--output",
        type=Path,
        help="New directory below output/releases/ (default: project-id-mode)",
    )
    parser.add_argument("--icc-profile", type=Path)
    parser.add_argument("--ghostscript", type=Path)
    parser.add_argument("--chrome", type=Path)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        release(args)
    except (ReleaseError, OSError, yaml.YAMLError) as error:
        print(f"RELEASE FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

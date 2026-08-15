# Safe Manifest Application

ZineOS Studio manifests are review handoffs. They do not gain repository write
authority merely because a browser exported them.

The application command is dry-run by default:

```sh
python scripts/apply_manifest.py path/to/manifest.json
```

When a placement introduces a source image, provide its creator-controlled
inbox explicitly:

```sh
python scripts/apply_manifest.py path/to/asset-placement.json \
  --asset-dir /absolute/path/to/photo-inbox
```

The command validates the manifest and prints the exact YAML diff plus planned
file copies. It writes nothing until the creator or Builder runs the reviewed
command with `--apply`.

```sh
python scripts/apply_manifest.py path/to/manifest.json \
  --asset-dir /absolute/path/to/photo-inbox \
  --apply
```

## Required Source Evidence

Every supported manifest identifies:

- its format and version;
- the publication project ID;
- the repository-relative Zine path;
- the SHA-256 of the exact YAML source used by Studio;
- stable page-unit and Block targets.

A changed YAML hash, project mismatch, missing target, stale original text, or
unsupported target blocks application. The Git commit is retained as useful
historical evidence, while the exact YAML hash is the blocking source check.

Older handoffs that contain only display page labels, Block indexes, or a Git
description are intentionally rejected. Re-export them from a current Studio
or translate them into stable IDs under creator review; do not guess targets.

## Asset Rules

- Source filenames must match exactly, including case and extension.
- Source file size must still match the exported handoff.
- Source paths cannot be supplied through the manifest.
- Original inbox files are never altered.
- Existing publication files are never overwritten with different bytes.
- New images receive a new asset ID, so unrelated uses of the old asset remain
  unchanged.
- Memory-grid application replaces only the selected cell.
- Crop and focal settings are stored with their target and consumed by the
  preview renderer for desktop and mobile output.
- A virtual free layer cannot be applied until an explicit publication Block
  exists for it.

## Text Rules

Text handoffs use `zineos-text-placement` version 1. Every edit contains a
stable page-unit ID, Block ID, field path, exact original text, replacement
text, and optional typography settings. Supported fields are inline content,
captions, checklist titles, and individual checklist-item text. Application
stops when the current target field does not exactly equal `originalText`.

Supported typography fields are font size, line height, width, x/y offset,
column count, and recorded rule spacing. The preview renderer applies the
general text controls; layout-specific decoration remains subject to visual
review.

## After Apply

An apply result is not creative approval. Run schema validation, build the exact
creator-facing preview, inspect asset integrity and responsive/print behavior,
and review the Git diff before committing.

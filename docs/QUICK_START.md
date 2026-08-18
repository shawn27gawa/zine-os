# ZineOS Quick Start

This guide takes a first-time creator from a photo folder to a validated local
review artifact. ZineOS keeps selection, sequence, crop, writing, and final
approval with the creator.

## 1. Prepare the repository

ZineOS requires Python 3.10 or newer. From the repository root:

```sh
python3 -m pip install -r requirements.txt
python3 scripts/check_setup.py
```

Chrome or Chromium, Ghostscript, and a licensed CMYK ICC profile are optional
for editing and review. They are required only for a formal CMYK print release.

## 2. Validate ZineOS

Run the same canonical repository validation used by CI:

```sh
python3 scripts/validate_zineos.py
```

The command checks dependencies, schemas, ZINE_001 asset integrity, Preview,
Unified Studio, manifest application, project bootstrap, print behavior,
release behavior, and a complete non-ZINE_001 workflow fixture. It writes only
ignored validation artifacts under `preview/` and temporary test directories.

## 3. Create a neutral project

Keep original photographs in a separate inbox. Preview the operation first:

```sh
python3 scripts/bootstrap_project.py \
  --project-id my-zine \
  --title "My Zine" \
  --language en \
  --creator "Creator Name" \
  --inbox /absolute/path/to/MY_PHOTO_INBOX \
  --output projects/my-zine \
  --dry-run
```

Remove `--dry-run` when the paths and project identity are correct. Bootstrap
creates a neutral four-page source and factual inbox inventory. It does not
select, copy, crop, rank, or sequence photographs.

## 4. Review and build

Open `projects/my-zine/INBOX_REVIEW.html` from its generated location. After the
creator selects material and approves an editorial structure, the Builder adds
only approved assets and Blocks to `zine.yaml`.

Build the editable Studio artifact:

```sh
python3 scripts/build_asset_studio.py \
  projects/my-zine/zine.yaml \
  preview/MY_ZINE_STUDIO.html
```

Studio exports image or text manifests; it does not write the repository.
Review a manifest as a dry run, then apply it explicitly:

```sh
python3 scripts/apply_manifest.py path/to/manifest.json \
  --asset-dir /absolute/path/to/MY_PHOTO_INBOX

python3 scripts/apply_manifest.py path/to/manifest.json \
  --asset-dir /absolute/path/to/MY_PHOTO_INBOX \
  --apply
```

Omit `--asset-dir` for a text-only manifest.

## 5. Create the creator-review release

```sh
python3 scripts/release_zine.py projects/my-zine/zine.yaml --mode review
```

Review the exact immutable artifact below `output/releases/`. A passing command
is mechanical evidence, not creative approval. The creator still approves the
visual result, commit, delivery, print, and merge.

For A5 saddle-stitch CMYK production, continue with
[Print Output](PRINT_OUTPUT.md) and [One-command Release](RELEASE_WORKFLOW.md).

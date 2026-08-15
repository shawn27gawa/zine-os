# ZineOS Unified Studio

Unified Studio is a local, review-first surface for assigning photographs,
recording creator-approved crop decisions, and editing publication text and
relevant typography in one exact preview.

It follows the ZineOS operating rule:

> The creator makes creative decisions. The agent implements, validates, and reports.

The Studio does not write publication files. It exports a placement manifest for Builder review and implementation. The publication YAML remains the source of truth.

## Build

```sh
python scripts/build_asset_studio.py \
  examples/ZINE_001/zine.yaml \
  preview/ZINE_001_STUDIO.html
```

Open the generated HTML in a browser. Drag image files onto outlined PHOTO,
GALLERY, CLOSEUP, memory-grid, or free-layer slots, or select outlined text to
edit it in the inspector. The historical script and stylesheet filenames retain
`asset` naming for command compatibility.

## Controls

For each selected slot, the creator can set:

- `cover` or `contain`;
- horizontal focal position;
- vertical focal position;
- scale;
- separate desktop and mobile values;
- free-layer page position and frame size where supported.

The Print view uses the desktop placement on the physical A5 preview surface. Final print review remains part of the standard creator-facing artifact workflow.

## Memory Grids

Memory-grid cells accept individual files. Dropping multiple files onto a cell fills the grid in filename order.

Grid photographs are shown in monochrome inside Studio. The source files remain unchanged. Front- and back-cover order and crop decisions remain creator-owned.

## Recipe-page Secondary Image

`recipe-page` layouts expose their existing PHOTO Blocks as editable slots. If a recipe page has no second PHOTO Block, Studio provides a reusable secondary free-layer slot instead. The current 28-page ZINE_001 edits the P10 Aperol glass through its existing PHOTO Block, so it does not display a duplicate empty layer.

The slot defaults to `contain` so the two glasses are not silently cropped. Bottle background removal is a separate, non-destructive asset-preparation task; Studio places the resulting transparent asset but does not generate or alter cutouts.

## Text Editing

Unified Studio exposes inline Block content, captions, questions, checklist
titles, and individual checklist items through stable page, Block, and field
targets. The inspector supports text, font size, line height, width, x/y
offset, and columns. Changes update only the in-memory exact preview until a
text manifest is exported.

Image and text handoffs remain separate, compatible manifest formats so each
can be validated, reviewed, and applied independently. Import accepts either
format only when project, publication path, source SHA-256, and stable targets
match the open Studio.

## Manifest

Use **Export images** or **Export text** to download the applicable JSON
handoff. Asset manifests record source filenames, placement settings, optional
local thumbnails, targets, and responsive overrides. Text manifests record
stable fields, exact original/replacement text, and optional typography. They
do not contain repository write authority.

Validate a manifest before Builder implementation:

```sh
python scripts/validate_asset_placement.py path/to/asset-placement.json
python scripts/validate_text_placement.py path/to/text-placement.json
```

Preview the exact publication diff without writing files:

```sh
python scripts/apply_manifest.py path/to/asset-placement.json \
  --asset-dir /absolute/path/to/photo-inbox
```

After reviewing the diff, add `--apply` to write the YAML change and copy new
images without overwriting an existing publication asset. See
[MANIFEST_APPLICATION.md](MANIFEST_APPLICATION.md) for the full safety contract.

The Builder uses the validated manifest to make a narrow, reviewable asset and YAML diff. The exact standard preview produced after that diff—not the in-memory Studio state—is the creator-facing approval artifact.

Importing a manifest restores settings and embedded review thumbnails when available. Original full-resolution source files are still required for final publication implementation.

## Safety Boundaries

- No backend, database, external API, runtime map service, or agent framework is used.
- No new browser or package dependency is required.
- Dragged files and text edits remain in browser memory until the creator exports a manifest.
- Original photographs are never modified.
- Studio cannot commit, push, publish, or merge.
- A manifest never replaces schema validation, preview building, asset-integrity checks, responsive review, print review, or creator approval.

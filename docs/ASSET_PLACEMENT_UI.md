# ZineOS Asset Placement UI

The Asset Placement UI is a local, review-first surface for assigning photographs and recording creator-approved crop decisions.

It follows the ZineOS operating rule:

> The creator makes creative decisions. The agent implements, validates, and reports.

The Studio does not write publication files. It exports a placement manifest for Builder review and implementation. The publication YAML remains the source of truth.

## Build

```sh
python scripts/build_asset_studio.py \
  examples/ZINE_001/zine.yaml \
  preview/ZINE_001_STUDIO.html
```

Open the generated HTML in a browser, then drag image files onto outlined PHOTO, GALLERY, CLOSEUP, memory-grid, or free-layer slots.

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

## Manifest

Use **Export manifest** to download a JSON handoff. The manifest records source filenames, placement settings, optional local thumbnails, targets, and responsive overrides. It does not contain repository write authority.

Validate a manifest before Builder implementation:

```sh
python scripts/validate_asset_placement.py path/to/asset-placement.json
```

The Builder uses the validated manifest to make a narrow, reviewable asset and YAML diff. The exact standard preview produced after that diff—not the in-memory Studio state—is the creator-facing approval artifact.

Importing a manifest restores settings and embedded review thumbnails when available. Original full-resolution source files are still required for final publication implementation.

## Safety Boundaries

- No backend, database, external API, runtime map service, or agent framework is used.
- No new browser or package dependency is required.
- Dragged files remain in browser memory until the creator exports a manifest.
- Original photographs are never modified.
- Studio cannot commit, push, publish, or merge.
- A manifest never replaces schema validation, preview building, asset-integrity checks, responsive review, print review, or creator approval.

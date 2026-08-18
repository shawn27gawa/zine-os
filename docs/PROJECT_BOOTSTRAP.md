# Project and Inbox Bootstrap

For dependency setup and the complete first-project sequence, begin with the
[Quick Start](QUICK_START.md).

ZineOS creates new publications from a neutral starter rather than copying
ZINE_001. ZINE_001 remains a completed example; its Europe route, writing,
photographs, layouts, and visual decisions are not new-project defaults.

The bootstrap workflow follows the operating rule:

> The creator makes creative decisions. The agent implements, validates, and reports.

## Create a project

Run a dry-run first:

```sh
python scripts/bootstrap_project.py \
  --project-id my-zine \
  --title "My Zine" \
  --language ja \
  --creator "Creator Name" \
  --inbox /absolute/path/to/MY_PHOTO_INBOX \
  --output projects/my-zine \
  --dry-run
```

Remove `--dry-run` to create the project. When `--output` is omitted, the
default is `projects/<project-id>`. Output must stay under `projects/` because
Studio manifests use safe repository-relative publication paths. The output
directory must not already exist; bootstrap refuses to overwrite it.

The generated project contains:

```text
projects/my-zine/
├── zine.yaml
├── assets/
├── inbox.inventory.json
├── INBOX_REVIEW.html
└── README.md
```

`zine.yaml` is a neutral, schema-valid four-page draft. It contains the
creator-supplied title but no selected photographs, travel route, inferred
story, or ZINE_001 content.

## Inbox inventory

Bootstrap reads JPEG, PNG, GIF, and WebP files recursively by default. Use
`--top-level-only` when nested folders should be excluded. Original files are
never renamed, copied, transformed, deleted, or written.

For each supported file, the inventory records:

- stable inventory-order candidate ID;
- filename and inbox-relative path;
- exact filename extension, detected file format, and mismatch evidence;
- byte size and SHA-256;
- pixel dimensions and orientation when readable;
- EXIF orientation for JPEG when present;
- duplicate-file evidence;
- `unassigned` selection status.

Candidate order is deterministic filename order. It is not a ranking,
recommendation, page sequence, or creative selection.

## Creator review

Open `INBOX_REVIEW.html` directly from its generated filesystem location. It
presents the factual inventory as a contact sheet with `UNASSIGNED` status.
Because the original inbox remains outside the project, do not relocate the
artifact or substitute a differently served HTTP copy when reviewing asset
integrity. The review page does not write project files or remember selections.

After review, the creator supplies selected candidate IDs and editorial intent.
The Editor scopes that direction, the Builder copies only approved assets into
`assets/` and creates a reviewable publication diff, and the Reviewer validates
the exact creator-facing artifact. Placement and crop remain creator decisions.

## Separation from ZINE_001

- `examples/ZINE_001/` is a completed reference publication.
- `templates/basic/` supplies format defaults, not a finished style.
- `scripts/bootstrap_project.py` removes example assets and content before
  writing a new draft.
- Unified Studio and the renderer operate on the new project's own `zine.yaml`.

No backend, database, external API, image-generation service, or new runtime
dependency is used.

# One-command Release

ZineOS release is a fail-fast orchestration layer over the existing validators,
preview renderer, Unified Studio, regression tests, and print builder. It does
not replace those components or write publication source.

## Review release

Use a review release during editing and creator approval:

```sh
python scripts/release_zine.py \
  examples/ZINE_001/zine.yaml \
  --mode review
```

The default output is:

```text
output/releases/<project-id>-review/
├── preview.html
├── studio.html
├── print/
│   ├── publication-print.html
│   ├── resolution-report.md
│   └── print-spec.txt
└── release-report.json
```

For a non-print publication, the print stage is recorded as
`NOT_APPLICABLE`. It is not reported as a print success.

## Formal print release

Formal print mode requires the locally installed tools and licensed ICC profile
used by the standard print pipeline:

```sh
python scripts/release_zine.py \
  examples/ZINE_001/zine.yaml \
  --mode print \
  --icc-profile /absolute/path/to/JapanColor2011Coated.icc
```

Chrome or Chromium and Ghostscript must be available. Optional `--chrome` and
`--ghostscript` paths may be supplied explicitly. Missing or invalid print
requirements stop the command before regression or artifact generation. A
formal print release additionally contains:

```text
pdf/rgb-proof.pdf
pdf/saddle-stitch-cmyk.pdf
```

The CMYK PDF remains subject to creator visual approval and physical proofing.
A successful command does not authorize printing, publishing, or merging.

## Release gates

The command runs these gates in order:

1. publication schema validation;
2. required asset integrity;
3. formal-print environment preflight when requested;
4. repository regression tests;
5. exact HTML preview build;
6. Unified Studio build;
7. applicable print build;
8. release report and artifact SHA-256 inventory.

Asset integrity blocks required references that are missing, unsafe,
case-mismatched, format-mismatched, or unknown. An unused asset is retained as
a warning because it may be an intentional source-library item. Warnings remain
visible in `release-report.json`.

## Immutable output

Release output must stay below `output/releases/`. The destination must not
already exist. To create another release, provide a new destination:

```sh
python scripts/release_zine.py \
  projects/my-zine/zine.yaml \
  --mode review \
  --output output/releases/my-zine-review-02
```

Artifacts are built in a temporary sibling directory. The destination appears
only after every gate passes. On failure, the temporary output is removed and
publication YAML and original assets remain unchanged.

This deliberately avoids `--force` or automatic cleanup. Overwriting or
deleting a creator-reviewed release must be a separate, exact creator action.

## Release report

`release-report.json` records:

- project and source YAML SHA-256;
- Git commit and clean/dirty working-tree evidence when available;
- SHA-256 hashes for the validators and generators used;
- schema, asset, regression, and print states;
- asset warnings;
- artifact paths, byte sizes, and SHA-256 hashes;
- release mode and creation time.

The report is validation evidence, not creative approval. The exact preview and
print artifact reviewed by the creator remain part of the validation target.

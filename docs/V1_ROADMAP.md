# ZineOS v1 Roadmap

ZineOS v1 is complete when a creator can move from a folder of source material
to an editable, reviewable, print-ready publication without losing creative
authority.

The target workflow is:

```text
photo inbox
-> publication structure
-> creator-approved initial placement
-> visual and text editing
-> saved publication source
-> exact creator preview
-> validation
-> A5 print proof
-> CMYK saddle-stitch PDF
```

## Completion Criteria

- A new publication can be created from a documented template.
- Source photographs can be inventoried without altering the originals.
- The creator can place, replace, crop, and position photographs in Studio.
- The creator can edit publication text and relevant typography controls.
- Studio changes can be validated and applied to publication source through a
  reviewable diff.
- Preview, Studio, and print output use the same publication source and asset
  references.
- A standard command validates the project and builds its review artifacts.
- A5 CMYK saddle-stitch output is reproducible from the repository.
- The complete workflow succeeds for a second publication, not only ZINE_001.

## Milestones

### 0. Foundation integration

Bring the creator-approved ZINE_001 source, Asset Placement Studio, print
package generator, tests, documentation, and CI onto one current branch without
changing the approved publication output.

### 1. Safe manifest application

Define compatible asset and text handoffs. Add validation, source-reference
checks, dry-run output, and an explicit apply step that produces a narrow YAML
diff. The browser must not write the repository directly.

### 2. Unified Studio

Combine image placement and text editing in one local creator-facing surface.
Support manifest export and import, desktop/mobile placement, and an exact
review preview. Preserve the publication YAML as the source of truth.

### 3. Project and inbox bootstrap

Create a new publication from the basic template, inventory a photo inbox, and
prepare creator-reviewable placement candidates. Do not silently select story,
sequence, imagery, or crop.

### 4. One-command release

Provide one documented command that runs schema checks, asset integrity,
preview generation, Studio generation, regression tests, and the applicable
print build.

### 5. Second-publication proof

Complete another publication from a new source folder. Remove any remaining
ZINE_001-only assumptions discovered by that test before declaring v1 complete.

## Non-goals

ZineOS v1 does not require a backend, database, external AI API, runtime map
service, agent framework, or proprietary editing format. It automates repeated
production work while the creator retains editorial and visual authority.

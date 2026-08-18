# ZineOS Standard Print Output

This document defines the creator-approved ZineOS print standard for an A5,
left-bound saddle-stitched publication. The standard was established from the
ZINE_001 Kinko's proofing cycle.

## Core Invariant

The finished A5 page is the source of truth. Bleed is generated outside the
finished page and must never introduce a second layout layer inside the trim.

A valid export must not contain a visible seam, scaled-layer boundary, white
fringe, or crop-mark artifact inside the TrimBox.

## Production Specification

- Finished page: A5 portrait, 148 x 210 mm.
- Binding: left-bound saddle stitch.
- Page count: a positive multiple of four.
- Delivery: one printer-order, imposed PDF.
- Bleed: 3 mm outside every outer trim edge.
- Crop marks: paired inner and outer corner marks. Inner marks identify the
  finished trim; outer marks identify the 3 mm bleed boundary.
- Crop-mark safety: each mark meets the BleedBox boundary without a visible
  gap and uses an explicit butt line cap so it stops at, rather than entering,
  publication artwork.
- Color: CMYK.
- OutputIntent: Japan Color 2011 Coated.
- Rendering intent: perceptual.
- Fonts: embedded.
- Images: CMYK or grayscale in the final PDF.

For an imposed A5 spread, the standard PDF boxes are:

| Box | Size |
| --- | --- |
| TrimBox | 296 x 210 mm |
| BleedBox | 302 x 216 mm |
| MediaBox | 322 x 236 mm |

The 10 mm difference between the BleedBox and each MediaBox edge holds crop
marks and production whitespace. It is not part of the finished publication.
The outer and inner marks are separated by the same 3 mm as the bleed. Each
7 mm vector path ends exactly at the BleedBox boundary and uses a butt cap.
Do not add a visible safety gap or extend a mark into the photograph area.

## Rendering Pipeline

The standard pipeline is:

```text
Zine YAML
-> one A5 HTML surface per logical page
-> A5 RGB review PDF in reader order
-> profile-managed CMYK A5 pages
-> 3 mm bleed added strictly outside TrimBox
-> generic saddle-stitch imposition
-> crop marks and OutputIntent
-> one creator-facing CMYK print PDF
```

The browser stage renders only one copy of each finished page. Do not recreate
the former approach that placed a scaled bleed copy beneath an unscaled trim
copy. That approach can expose the bleed layer inside the TrimBox and create a
visible line at the page edge.

During PDF normalization, each single finished-page surface receives a uniform
sub-millimeter overscan before it is clipped to the exact A5 TrimBox. This
compensates for browser page-size rounding at the right and bottom edges; it is
not a second bleed layer and must not create an internal boundary.

## Standard Command

An official Japan Color 2011 Coated CMYK ICC profile is required locally. The
profile is not stored in this repository because its redistribution terms must
be respected.

```sh
python3 scripts/build_print_package.py \
  projects/my-zine/zine.yaml \
  --icc-profile /absolute/path/to/JapanColor2011Coated.icc
```

By default, artifact names are derived from `project.id`. For `my-zine`, the
standard final artifact is written to:

```text
output/pdf/MY_ZINE_SADDLE_STITCH_CMYK_PRINT.pdf
```

The build also writes an A5 RGB review PDF, a resolution report, and a print
specification. The CMYK file is the printer-delivery artifact; the RGB file is
not a substitute for it.

## Imposition

Imposition is calculated from the page count rather than hardcoded for one
publication. For 28 pages, the first and last imposed sides are:

```text
P28 | P1
P2  | P27
...
P14 | P15
```

The inner edge at the fold has no artificial bleed gap. The outer perimeter of
each imposed side retains 3 mm bleed.

## Required Validation

Before delivery, verify:

1. Schema validation passes for the publication.
2. `python scripts/test_print_package.py` passes.
3. The final PDF has the expected logical and imposed page counts.
4. MediaBox, TrimBox, and BleedBox match the dimensions above.
5. The OutputIntent identifies Japan Color 2011 Coated and has four components.
6. Images are CMYK or grayscale and fonts are embedded.
7. Required assets resolve from the exact final build environment.
8. Every imposed side renders without PDF errors.
9. Trimmed page content matches the creator-approved preview.
10. Full-bleed edges contain no internal seam or white fringe.
11. Paired inner and outer crop marks are present at all four corners; each
    pair is separated by exactly 3 mm.
12. The crop marks visibly meet the BleedBox edge without a gap, use butt line
    caps, and do not extend into publication imagery.
13. The exact PDF sent to the printer is the artifact reviewed by the creator.

Image-resolution warnings remain evidence for review, not permission to replace
or reinterpret creator-selected photographs. ZINE_001's current image
resolution was accepted after a physical proof.

## Printer Handoff

Describe the artifact as an A5, left-bound saddle-stitch, printer-order CMYK PDF
with 3 mm bleed and crop marks. Ask the receiving store to confirm stock,
quantity, and production settings before printing. Do not let a printer-side
request silently change trim size, page order, color mode, or creator-approved
layout.

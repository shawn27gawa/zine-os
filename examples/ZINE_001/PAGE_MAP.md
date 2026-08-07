# ZINE_001 — Page Map

This document translates the original hand-drawn sketches for `ZINE_001` into a structured editorial page map.

The purpose of this document is to preserve the intent of the sketches before converting the publication into a more detailed `zine.yaml`.

This is a working document.

Anything that cannot yet be confidently interpreted from the sketches is marked as `TBD` rather than being invented.

---

# Publication Overview

**Working title:** Our Memory  
**Current length:** 26 pages  
**Primary medium:** Print  
**Orientation:** Portrait  
**Editorial character:** Personal, photographic, reflective, imperfect, memory-driven

The publication combines:

- photographs
- maps
- handwritten elements
- lists
- questions
- short writing
- close-up details
- visual grids
- full-spread images

---

# Page Structure

## Page 1 — Memory Index

### Purpose

Opening index based on memory rather than conventional navigation.

### Content

- title: `OUR MEMORY`
- grid of cells
- some cells filled
- some cells left empty

### Editorial idea

Filled cells represent memories that exist, have been recorded, or carry significance.

Empty cells represent:

- memories not yet recorded
- unfinished experiences
- forgotten moments
- space for future memories

### Proposed ZineOS representation

```text
TEXT
+
MEMORY INDEX LAYOUT
```

### Layout

```text
memory-index-grid
```

### Status

Defined conceptually.

Exact grid dimensions and filled-cell positions should be confirmed from the original sketch.

---

## Pages 2–3 — Place and Route

### Page 2

Large photograph with a small location or address reference near the bottom.

### Page 3

Map-based page showing:

- route
- geographic relationship
- location pins
- movement between places

### Proposed Blocks

```text
PHOTO
CAPTION / LOCATION
MAP
```

### Editorial role

Establish where the memory took place.

---

## Pages 4–5 — Fragmented Memory Gallery

A photographic sequence spread across two pages.

### Page 4

- two photographs
- large amount of surrounding space
- repeated wave-like visual motif

### Page 5

- approximately three photographs
- vertical composition
- same wave-like visual motif

### Proposed Blocks

```text
GALLERY
```

### Layout

```text
asymmetric-gallery
```

### Style note

The wave-like elements should be treated as visual styling rather than editorial Blocks.

---

## Pages 6–7 — Full Spread Photograph

A single photograph dominates the entire spread.

### Proposed Block

```text
PHOTO
```

### Layout

```text
full-bleed-spread
```

### Editorial role

A visual pause and high-impact memory moment.

---

## Pages 8–9 — Drink / Recipe Memory

### Page 8

Contains:

- photograph
- short recipe or descriptive text
- illustrated bottle labeled `APEROL`

### Page 9

Contains:

- photograph
- short written material underneath
- simple horizontal or wave-like graphic elements

### Proposed Blocks

```text
PHOTO
RECIPE
ILLUSTRATION
TEXT
```

### ZineOS observation

`RECIPE` is not currently part of Block Library v0.1.

This real publication provides evidence that a `RECIPE` Block may be useful.

---

## Pages 10–11 — Image and Recorded Sequence

### Page 10

Large photograph occupying most of the page.

### Page 11

A sequence of horizontal lines containing small markers or symbols.

### Proposed Blocks

```text
PHOTO
TIMELINE
```

### Status

The exact meaning of the markers on Page 11 is currently `TBD`.

The structure appears sequential, so `TIMELINE` is the closest existing Block candidate.

---

## Pages 12–13 — Detail and Context

### Page 12

Two close-up images surrounded by short words or annotations.

### Proposed Blocks

```text
CLOSEUP
CLOSEUP
CAPTION
```

### Page 13

Large photograph with short supporting text.

### Proposed Blocks

```text
PHOTO
TEXT
```

### Editorial role

Move between detail and wider context.

---

## Pages 14–15 — Image Pair with Text

### Page 14

Large standalone photograph.

### Page 15

Combination of:

- photograph positioned toward the upper-right area
- written text positioned separately below or toward the left

### Proposed Blocks

```text
PHOTO
TEXT
```

### Layout

```text
image-text-offset
```

---

## Pages 16–17 — Full Spread Photograph

One large photograph spanning both pages.

### Proposed Block

```text
PHOTO
```

### Layout

```text
full-bleed-spread
```

### Editorial role

Second major visual pause in the publication.

---

## Pages 18–19 — Multi-Image Narrative

### Page 18

Approximately two photographs with short text placed nearby.

### Page 19

Approximately two photographs with a more layered or overlapping composition.

### Proposed Blocks

```text
GALLERY
CAPTION
TEXT
```

### Layout

```text
editorial-collage
```

---

## Pages 20–21 — Writing and Image

### Page 20

Primarily written material.

### Proposed Block

```text
TEXT
```

or, depending on final length:

```text
ESSAY
```

### Page 21

Large photograph.

### Proposed Block

```text
PHOTO
```

### Editorial role

A deliberate transition from language back into image.

---

## Pages 22–23 — Future Lists

### Page 22

Title from the original sketch:

```text
Things I / We Want to Do
```

Contains a list of future actions or wishes.

### Page 23

A second list that appears to relate specifically to things the two people want to do together.

### Proposed Blocks

```text
CHECKLIST
CHECKLIST
```

### Editorial role

Shift the publication from remembered experiences toward future possibility.

### Status

Exact titles should be confirmed from the original handwritten text.

---

## Pages 24–25 — Photograph and Question

### Page 24

Large photograph.

### Proposed Block

```text
PHOTO
```

### Page 25

Reflective question followed by space for written response.

Approximate meaning from the sketch:

```text
Where do you want to go?
```

### Proposed Block

```text
QUESTION
```

### Editorial role

Invite reflection rather than simply present another memory.

---

## Page 26 — Closing Grid

The final page contains a repeated grid-like collection of shapes.

The exact editorial meaning is not yet fully defined.

### Possible relationship

This page may visually echo the Memory Index on Page 1.

If so, the publication could begin and end with related memory structures.

```text
OPENING
Memory Index

↓

memories, places, photographs, writing

↓

ENDING
Memory Grid
```

### Proposed representation

```text
TBD
```

Possible future interpretations include:

- evolved Memory Index
- memory completion map
- visual archive
- closing gallery
- intentionally unresolved grid

No final interpretation should be assigned until the creator confirms the intended meaning.

---

# Editorial Rhythm

The current sketch suggests the following rhythm:

```text
INDEX
↓
PLACE
↓
GALLERY
↓
FULL-SPREAD IMAGE
↓
OBJECT / RECIPE
↓
IMAGE + SEQUENCE
↓
DETAIL
↓
IMAGE + TEXT
↓
FULL-SPREAD IMAGE
↓
COLLAGE
↓
WRITING
↓
FUTURE LISTS
↓
QUESTION
↓
CLOSING GRID
```

The publication alternates between dense and sparse pages rather than maintaining constant information density.

This variation should be preserved.

---

# Visual Rhythm

The sketches suggest several recurring visual behaviors:

## Large Images

Pages:

```text
6–7
14
16–17
21
24
```

Large images act as pauses in the publication.

---

## Multi-Image Pages

Pages:

```text
4–5
12
18–19
```

These pages increase visual density and create contrast with the large-image pages.

---

## Text-Driven Pages

Pages:

```text
11
20
22–23
25
```

These slow the visual sequence and shift attention toward reflection.

---

# New Block Candidates Discovered Through Practice

Building this real publication reveals editorial needs that were not included in Block Library v0.1.

## RECIPE

Strong candidate.

The Page 8 sketch contains both an object or photograph and recipe-like information.

A `RECIPE` Block could represent structured information such as:

```yaml
type: RECIPE
title: Aperol Spritz
ingredients:
  - ingredient: Aperol
    amount: TBD
  - ingredient: Prosecco
    amount: TBD
instructions:
  - TBD
```

This Block should only be added after confirming that the recipe is intended as structured editorial content rather than ordinary text.

---

## LOCATION

Possible candidate.

Page 2 combines a photograph with geographic or address information.

A `LOCATION` Block may eventually represent:

```text
place name
address
coordinates
date
short note
```

For now, `CAPTION` can represent this information.

---

## MEMORY_INDEX

Possible candidate.

The opening page has a strong editorial function that is not fully captured by `TEXT` or `GALLERY`.

However, a dedicated `MEMORY_INDEX` Block should not be added solely because one page uses it.

If the concept appears repeatedly or becomes reusable across multiple publications, it may graduate into the Block Library.

---

# ZineOS Design Lessons from ZINE_001

This publication already reveals several useful principles.

### 1. Layout meaning matters

A page can have editorial meaning beyond its Blocks.

The Memory Index demonstrates why semantic Layout types are useful.

### 2. Decorative elements are not necessarily Blocks

The repeated wave motif should remain part of visual styling unless it carries editorial meaning.

### 3. Real publications should drive Block evolution

The appearance of recipe-like content provides stronger evidence for a new Block than theoretical brainstorming.

### 4. Empty space carries meaning

Blank or unfinished areas should not automatically be treated as missing content.

In this publication, absence itself may be part of the editorial structure.

---

# Status

```text
Page mapping:          Draft
Editorial sequence:    Draft
Block assignment:      Draft
Final text:            Not started
Real assets:           Not connected
Layout implementation: Not started
Rendering:             Not started
```

The next step is to confirm ambiguous page meanings, then translate this map into the complete `ZINE_001/zine.yaml`.

# ZineOS Publication Format

This document defines the conceptual structure used to represent a publication in ZineOS.

The goal of the ZineOS format is to describe a publication independently from any specific design application, renderer, or AI system.

A ZineOS publication should describe what the publication is before describing exactly how it should look.

---

## Core Structure

A ZineOS publication consists of five primary layers:

```text
PROJECT
│
├── METADATA
├── ASSETS
├── SEQUENCE
├── PAGES
└── OUTPUT
```

---

## 1. Project

The Project represents the publication as a whole.

It contains information such as:

- title
- project identifier
- description
- language
- publication format
- page count
- creation date
- project status

Example:

```yaml
project:
  id: zine-001
  title: Our Memory
  language: en
  status: draft
```

---

## 2. Metadata

Metadata describes information about the publication that is not part of the page content itself.

Examples include:

- creator
- contributors
- edition
- publication date
- tags
- copyright information
- license
- notes

Example:

```yaml
metadata:
  creator: Example Creator
  edition: 1
  tags:
    - travel
    - memory
    - photography
```

---

## 3. Assets

Assets are the source materials used to build the publication.

Examples include:

- photographs
- illustrations
- text files
- maps
- scans
- handwritten notes
- audio transcripts
- external references

Assets should be referenced rather than permanently embedded into the publication structure whenever practical.

Example:

```yaml
assets:
  - id: photo-001
    type: image
    source: assets/photo-001.jpg

  - id: essay-001
    type: text
    source: content/essay-001.md
```

---

## 4. Sequence

Sequence describes the editorial flow of the publication.

It answers the question:

> In what order should the reader experience the material?

Sequence is separate from visual layout.

For example:

```yaml
sequence:
  - opening
  - journey
  - memory
  - reflection
  - ending
```

This allows the editorial structure to remain understandable even if the visual design changes.

---

## 5. Pages

Pages describe how editorial material is assigned to physical or digital pages.

Each page may contain one or more Blocks.

Example:

```yaml
pages:
  - number: 1
    blocks:
      - type: PHOTO
        asset: photo-001

  - number: 2
    blocks:
      - type: ESSAY
        asset: essay-001
```

Pages may also be grouped into spreads.

Example:

```yaml
pages:
  - spread: [4, 5]
    blocks:
      - type: PHOTO
        asset: photo-004
```

---

## Blocks

Blocks are reusable editorial units.

Initial Block types may include:

```text
PHOTO
TEXT
ESSAY
QUOTE
CAPTION
MAP
GALLERY
CHECKLIST
QUESTION
TIMELINE
CLOSEUP
```

A Block describes editorial purpose before visual appearance.

For example:

```yaml
- type: PHOTO
  asset: photo-012
```

does not automatically mean that the photograph must fill the page.

Visual interpretation belongs to the layout and rendering layers.

---

## Layout

Layout describes how Blocks are arranged visually.

Layout is intentionally separate from content and editorial structure.

For example:

```yaml
layout:
  type: full-bleed
```

or:

```yaml
layout:
  type: image-left-text-right
```

ZineOS should allow Layout definitions to evolve without changing the underlying content.

---

## Output

Output describes the intended publication destination.

Examples include:

- print
- PDF
- browser
- EPUB
- image sequence

Example:

```yaml
output:
  format: print
  page_size: A5
  binding: saddle-stitch
```

Output settings should not redefine the editorial structure of the publication.

---

## Separation of Concerns

The ZineOS format follows this hierarchy:

```text
CONTENT
↓
EDITORIAL SEQUENCE
↓
PAGE STRUCTURE
↓
LAYOUT
↓
RENDERING
↓
OUTPUT
```

Each layer should remain as independent as practical.

This allows the same ZineOS publication to be rendered through different tools and technologies.

For example:

```text
                 ┌── HTML
                 │
ZineOS Project ──┼── PDF
                 │
                 ├── Figma
                 │
                 └── Future Renderer
```

---

## Source of Truth

The ZineOS project format is the source of truth for the publication.

Figma files, PDFs, HTML previews, and other rendered outputs are representations of that source.

They should not become the only place where the publication structure exists.

---

## Design Goal

A creator should be able to open a ZineOS project years later and understand:

- what materials were used
- how the publication was structured
- why materials were ordered in a particular way
- which layout choices were made
- how the publication was intended to be produced

without requiring the original design software.

**The publication should outlive the tools used to create it.**

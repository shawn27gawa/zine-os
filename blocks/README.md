# ZineOS Block Library

The Block Library defines the reusable editorial units used to construct publications in ZineOS.

A Block describes the editorial purpose of a piece of content before defining its exact visual appearance.

Blocks are intentionally simple, composable, and independent from any specific renderer or design application.

---

## What Is a Block?

A Block is the smallest meaningful editorial unit in a ZineOS publication.

Examples include:

- a photograph
- an essay
- a quote
- a map
- a gallery
- a checklist
- a question

A Block answers:

> What role does this content play in the publication?

It does not necessarily answer:

> Exactly where and how should this content be drawn?

Visual interpretation belongs primarily to the layout and rendering layers.

---

## Core Principle

```text
CONTENT
↓
BLOCK
↓
LAYOUT
↓
RENDERER
```

For example:

```yaml
type: PHOTO
asset: photo-001
```

describes a photograph used as editorial content.

The same Block could later appear as:

- a full-page image
- a small image surrounded by whitespace
- part of a grid
- one side of a spread

without changing the underlying Block type.

---

# Block Library v0.1

The initial Block Library contains the following Block types.

---

## 1. PHOTO

Represents a single photograph or image.

Typical uses:

- documentary photography
- visual storytelling
- opening images
- standalone images
- visual pauses

Example:

```yaml
- type: PHOTO
  asset: photo-001
```

---

## 2. TEXT

Represents a short piece of general text.

Typical uses:

- introductions
- short notes
- labels
- short reflections
- ending text

Example:

```yaml
- type: TEXT
  content: "A short piece of text."
```

---

## 3. ESSAY

Represents a longer written passage.

Typical uses:

- essays
- travel writing
- personal reflections
- editorial writing
- narrative passages

Example:

```yaml
- type: ESSAY
  asset: essay-001
```

---

## 4. QUOTE

Represents a highlighted quotation or standalone phrase.

Typical uses:

- memorable statements
- dialogue
- thematic phrases
- excerpts

Example:

```yaml
- type: QUOTE
  content: "Some memories only exist because we wrote them down."
```

---

## 5. CAPTION

Represents supporting text associated with another Block.

Typical uses:

- image captions
- dates
- locations
- context
- credits

Example:

```yaml
- type: CAPTION
  content: "Christchurch, August 2026"
```

---

## 6. MAP

Represents geographic or spatial information.

Typical uses:

- travel routes
- locations
- neighborhoods
- journeys
- spatial relationships

Example:

```yaml
- type: MAP
  asset: map-001
```

---

## 7. GALLERY

Represents a collection of related visual assets.

Typical uses:

- photo collections
- visual indexes
- contact-sheet layouts
- collections of objects
- memory grids

Example:

```yaml
- type: GALLERY
  assets:
    - photo-001
    - photo-002
    - photo-003
    - photo-004
```

---

## 8. CHECKLIST

Represents a list of items that may be complete, incomplete, remembered, planned, or compared.

Typical uses:

- things we did
- things we wanted to do
- packing lists
- recommendations
- future plans

Example:

```yaml
- type: CHECKLIST
  items:
    - text: "Visit the lake"
      checked: true

    - text: "Return in winter"
      checked: false
```

---

## 9. QUESTION

Represents a prompt intended to create reflection, participation, or narrative interruption.

Typical uses:

- personal questions
- interview prompts
- reader participation
- memory prompts
- reflective pages

Example:

```yaml
- type: QUESTION
  content: "What place would you return to?"
```

---

## 10. TIMELINE

Represents events organized through time or sequence.

Typical uses:

- travel chronology
- historical events
- daily routines
- project histories
- memory sequences

Example:

```yaml
- type: TIMELINE
  items:
    - time: "06:30"
      text: "Left the city"

    - time: "10:15"
      text: "Reached the mountains"
```

---

## 11. CLOSEUP

Represents a deliberate detail or cropped view derived from another visual asset.

Typical uses:

- emphasizing details
- visual comparison
- zoom sequences
- revealing overlooked elements

Example:

```yaml
- type: CLOSEUP
  asset: photo-001
  region:
    x: 0.35
    y: 0.20
    width: 0.30
    height: 0.30
```

The exact crop implementation may vary between renderers.

---

## Common Block Fields

Where appropriate, Blocks may share common fields.

```yaml
id: block-001
type: PHOTO
```

Possible common fields include:

```text
id
type
asset
assets
content
caption
metadata
role
```

Not every Block requires every field.

Block-specific schemas will define which fields are required or optional.

---

## Blocks and Layouts

Block type and Layout type must remain separate concepts.

For example:

```yaml
blocks:
  - type: PHOTO
    asset: photo-001

layout:
  type: full-page
```

The Block describes what the content is.

The Layout describes how that content is presented.

This separation allows the same content to be redesigned without rewriting the publication structure.

---

## Composability

Multiple Blocks may appear on the same page or spread.

Example:

```yaml
blocks:
  - type: PHOTO
    asset: photo-001

  - type: CAPTION
    content: "Day 03"

  - type: TEXT
    content: "We arrived before sunrise."
```

Renderers may interpret this structure in different ways.

---

## Extensibility

The Block Library is not intended to be permanently limited to the initial types.

Future Blocks may include:

```text
INTERVIEW
RECIPE
OBJECT
DIAGRAM
TABLE
INDEX
CREDITS
LOCATION
AUDIO
HANDWRITING
```

New Blocks should be introduced only when they represent a meaningful editorial role that cannot be expressed clearly using existing Blocks.

---

## Block Design Rules

Every ZineOS Block should follow these principles:

1. A Block represents editorial meaning before visual appearance.
2. A Block should have one clear primary responsibility.
3. Blocks should remain reusable across different publications.
4. Blocks should not depend on a specific design application.
5. Blocks should be understandable by both humans and software.
6. Visual styling should remain separate from Block meaning.
7. New Block types should solve real editorial needs rather than duplicate existing ones.
8. Blocks should remain editable and replaceable.

---

## Status

This is the initial Block Library for ZineOS v0.1.

The definitions are expected to evolve as real publications are built with the system.

The Block Library should grow from actual editorial practice rather than theoretical completeness.

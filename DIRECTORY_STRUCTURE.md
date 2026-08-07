# ZineOS Directory Structure

This document defines the initial repository structure of ZineOS.

ZineOS should begin with a small, understandable structure and expand only when new responsibilities actually appear.

The goal is to keep the repository easy to navigate, easy to contribute to, and easy to maintain.

---

## Initial Structure

```text
zine-os/
│
├── README.md
├── MANIFESTO.md
├── DESIGN_PRINCIPLES.md
├── ARCHITECTURE.md
├── DIRECTORY_STRUCTURE.md
├── LICENSE
│
├── docs/
│
├── blocks/
│
├── schema/
│
├── templates/
│
├── examples/
│
├── agents/
│
├── preview/
│
└── integrations/
```

---

## 1. docs/

The `docs/` directory contains documentation that explains how ZineOS works, how it evolves, and how contributors can understand the project.

Possible contents include:

- vision documents
- specifications
- RFCs
- tutorials
- terminology
- development notes
- contribution guides

The directory may later expand into a structure such as:

```text
docs/
├── guides/
├── specifications/
├── rfcs/
└── concepts/
```

The documentation structure should remain simple until additional separation becomes necessary.

---

## 2. blocks/

The `blocks/` directory defines the editorial building blocks used by ZineOS.

A Block represents a reusable editorial unit.

Examples include:

```text
PHOTO
ESSAY
QUOTE
MAP
GALLERY
CHECKLIST
QUESTION
TIMELINE
CAPTION
CLOSEUP
```

In the early stages of ZineOS, each Block may be described using Markdown.

A Block definition may include:

- purpose
- expected inputs
- possible outputs
- editorial role
- constraints
- examples

Future versions may include executable implementations, renderers, or plugins associated with Blocks.

---

## 3. schema/

The `schema/` directory defines the data structures used by ZineOS.

This directory is intended to become one of the core parts of the project.

Possible files include:

```text
zine.schema.json
block.schema.json
project.schema.json
```

ZineOS should describe a publication independently from the software used to edit or render it.

The schema provides the common language that allows different tools, renderers, agents, and integrations to work with the same publication structure.

---

## 4. templates/

The `templates/` directory contains starter structures for new ZineOS projects.

Examples may include:

```text
project-template/
travel-zine/
photo-zine/
essay-zine/
```

Templates should not impose a finished visual style.

They should provide useful starting structures that creators can modify, remove, or replace.

Templates are conveniences, not rules.

---

## 5. examples/

The `examples/` directory contains complete or partial examples of publications created with ZineOS.

Possible categories include:

```text
examples/
├── travel/
├── photography/
├── essay/
└── experimental/
```

Examples should help users understand:

- how Blocks are combined
- how project files are structured
- how editorial sequences are represented
- how different renderers may interpret the same structure

The first real ZineOS publication should also serve as the first major example project.

---

## 6. agents/

The `agents/` directory defines optional software-assisted editorial roles.

Initial roles may include:

```text
Curator
Editor
Art Director
Reviewer
```

Agents should be defined by their responsibilities rather than by a specific AI model.

For example:

### Curator

Helps organize, compare, and select materials.

### Editor

Helps propose narrative structure, sequence, and editorial rhythm.

### Art Director

Helps propose visual relationships, hierarchy, and layout direction.

### Reviewer

Helps identify inconsistencies, repetition, readability issues, and structural problems.

Agent outputs should always remain suggestions.

The creator remains the final decision-maker.

---

## 7. preview/

The `preview/` directory contains tools for reviewing a publication before final export.

Possible preview modes include:

- single-page view
- spread view
- thumbnail overview
- reading sequence
- print simulation
- page rhythm overview

The initial implementation may use a browser-based HTML preview.

Preview should support editorial decision-making, not only technical validation.

---

## 8. integrations/

The `integrations/` directory contains optional connections between ZineOS and external tools.

Possible integrations include:

```text
integrations/
├── figma/
├── obsidian/
└── future-tools/
```

External tools should remain adapters around ZineOS rather than becoming part of its core architecture.

ZineOS should not depend on Figma, Obsidian, Adobe software, or any particular AI platform in order for a project to remain understandable and usable.

---

## Directory Design Principles

The ZineOS repository structure should follow these principles:

1. Keep the initial structure small.
2. Give each directory one clear responsibility.
3. Avoid premature abstraction.
4. Avoid organizing the core system around proprietary tools.
5. Keep files understandable to humans whenever possible.
6. Add new directories only when a real architectural responsibility appears.
7. Prefer predictable names over clever names.
8. Keep integrations separate from core publication logic.

---

## Current Core Directories

For the initial version of ZineOS, the core directories are:

```text
docs/
blocks/
schema/
templates/
examples/
agents/
preview/
integrations/
```

This structure is intentionally minimal.

Future directories should be added only when the project has a concrete need for them.

**Structure should grow with the project, not ahead of it.**

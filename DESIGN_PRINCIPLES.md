# ZineOS Design Principles

These principles guide how ZineOS is designed, developed, and extended.

They are not visual style rules.

They define how the system should behave.

---

## 01. Human First

The creator is always the final decision-maker.

ZineOS may suggest, organize, analyze, generate alternatives, and identify problems.

It should never silently replace meaningful creative decisions.

Human decisions always win.

---

## 02. Creativity Is Not the Automation Target

ZineOS automates repetitive and mechanical work.

It should reduce time spent on:

- repetitive layout operations
- file organization
- image preparation
- formatting
- consistency checks
- export preparation

The goal is not to remove creative work.

The goal is to create more time for it.

---

## 03. Everything Should Be Editable

No generated result should become a black box.

Layouts, blocks, metadata, AI suggestions, sequences, and project structures should remain understandable and editable.

Whenever possible, changes should also be reversible.

ZineOS should propose states, not lock creators into them.

---

## 04. Open Formats First

A ZineOS project should not depend on a single proprietary application.

Core project information should use open, human-readable formats whenever practical.

Examples include:

- Markdown
- YAML
- JSON
- HTML
- standard image formats
- PDF for distribution and print

A creator should be able to understand the basic structure of a project without ZineOS itself.

---

## 05. Blocks, Not Templates

ZineOS should provide small reusable editorial components rather than forcing complete predefined designs.

A block may represent:

- a photograph
- an essay
- a quote
- a map
- a gallery
- a checklist
- a timeline
- a question
- a caption

Blocks can be combined, modified, replaced, or ignored.

Templates may exist, but they should be compositions of understandable blocks.

---

## 06. Structure and Style Are Separate

Content structure should not be permanently tied to visual appearance.

The same story structure should be capable of producing different visual interpretations.

For example:

`PHOTO + ESSAY + MAP`

should describe editorial structure without requiring one specific font, grid, color, or layout.

This separation allows ZineOS projects to move between renderers, tools, and styles.

---

## 07. Print Is a First-Class Medium

ZineOS should understand that a publication is a physical object.

It should account for concepts such as:

- page size
- spreads
- margins
- bleed
- binding
- page count
- image resolution
- print-safe output

Digital publishing is welcome.

Print should never be treated as an afterthought.

---

## 08. Progressive Complexity

A beginner should be able to make a simple zine without understanding the entire system.

Advanced users should still be able to access deeper controls.

The basic workflow should remain simple:

Idea → Material → Edit → Arrange → Review → Publish

Complexity should appear only when the creator needs it.

---

## 09. Tool Independence

ZineOS is not Figma.

ZineOS is not Obsidian.

ZineOS is not Adobe.

ZineOS is not any particular AI model.

These tools may connect to ZineOS, but they should never define ZineOS.

The core system should survive changes in applications, platforms, and AI technologies.

---

## 10. Local and Portable by Default

Creators should be able to keep their projects as ordinary files and folders.

A project should be easy to:

- copy
- back up
- version
- archive
- move between computers
- store in Git

Cloud services may improve the experience, but they should not become a requirement for owning or accessing a project.

---

## 11. AI Must Be Inspectable

When AI contributes to the workflow, its role should be visible.

Creators should be able to distinguish between:

- original material
- human decisions
- AI suggestions
- generated alternatives

AI should assist the editorial process without obscuring authorship.

---

## 12. Imperfection Is a Feature

ZineOS should not optimize every publication toward visual uniformity.

Rules may be intentionally broken.

Layouts may be asymmetric.

Pages may be empty.

Images may be awkwardly cropped.

Handwritten elements may remain handwritten.

The system should support intentional irregularity rather than correcting it automatically.

---

## The Core Rule

When there is a conflict between automation and creative control:

**Creative control wins.**

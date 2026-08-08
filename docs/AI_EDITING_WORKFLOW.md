# ZineOS Studio v0.3 — AI-Native Editing Workflow

ZineOS uses AI to reduce mechanical editing work while keeping authorship and creative direction with the creator.

> The creator makes creative decisions. The agent implements, validates, and reports.

> We don't automate creativity. We automate repetition.

The authoritative operating contract is [`AGENTS.md`](../AGENTS.md). This guide explains how its roles hand work to one another. They are conceptual accountability boundaries, not an agent framework or a claim that multiple autonomous processes exist.

## ZineOS Studio v0.2.1 Review Baseline

ZineOS Studio v0.2.1 established this rule:

> The artifact reviewed by the creator is part of the validation target.

The Reviewer identifies the exact creator-facing artifact and compares its environment with the validation and visual-regression environments. Internal evidence is not interchangeable with the artifact the creator receives when path resolution, asset reachability, serving mode, viewport behavior, fonts, CSS, JavaScript, responsive behavior, or print behavior could differ.

For relevant creator-facing pages and spreads, asset evidence uses **ASSET PASS**, **ASSET FAIL**, or **ASSET UNVERIFIED**. A required broken asset blocks approval. Relative paths are evaluated from the artifact's actual resolved location; symlinked and lexical output paths are not assumed equivalent.

These v0.2.1 gates remain mandatory in v0.3.

## Complete Workflow

```text
Creator intent
→ Editor
→ specialist evidence or visual options when needed
→ creator direction when required
→ Builder
→ validation
→ creator-facing artifact and asset verification
→ visual regression
→ Reviewer
→ creator approval
→ Publisher when authorized
→ PR when authorized
→ creator merge approval
```

A single Codex session may perform several roles, but it must label transitions and preserve each approval boundary. One role cannot use another role's authority to choose a creative direction, repair its own review findings silently, publish without authorization, or merge.

## Role Responsibilities

### Creator

The Creator owns final decisions about story, sequence, layout, imagery, crop, typography, whitespace, rhythm, intentional irregularity, visual acceptance, and merge approval.

### Editor

The Editor interprets intent, establishes scope and risk, identifies what must be preserved, inspects Git history for restoration work, and produces the implementation brief. Material visual ambiguity is routed to the Art Director rather than resolved silently.

### Art Director

The Art Director analyzes composition and develops two or three materially distinct options when visual direction requires creator choice. It explains tradeoffs and returns the creator-selected direction as an explicit brief. It does not select or implement.

### Asset Curator

The Asset Curator inventories relevant media, verifies references and basic properties, distinguishes asset, crop, focal-point, renderer, path, and layout problems, and reports factual evidence. It does not replace, delete, crop, or rank imagery without creator direction.

### Builder

The Builder receives the approved brief, implements the smallest coherent diff, preserves unrelated behavior and responsive/print separation, runs validation, and builds the exact creator-review artifact. It does not reinterpret the brief or declare creative approval.

### Reviewer

The Reviewer independently checks scope, diff, mechanical validation, asset integrity, environment parity, visual regression, responsive/print evidence, and the exact creator-facing artifact. It reports missing evidence and never silently repairs the implementation.

### Publisher

The Publisher packages only creator-approved work after review. It stages, commits, pushes, or opens a PR only with authorization and never merges autonomously.

## Task-Specific Orchestration

### Simple LOW-risk mechanical task

```text
Creator → Editor → Builder → Reviewer → creator approval if visual → Publisher when authorized
```

### Aesthetic task with meaningful ambiguity

```text
Creator → Editor → Art Director → creator selects direction → Builder
→ Asset Curator when media is involved → Reviewer → creator approval → Publisher
```

### Media-heavy task

```text
Creator → Editor → Asset Curator → Art Director if composition is involved
→ creator direction → Builder → Reviewer → creator approval → Publisher
```

### Historical restoration

```text
Creator → Editor → Git history → Art Director when multiple appearances are plausible
→ creator chooses target → Builder → Asset Curator when assets are involved
→ Reviewer → creator approval → Publisher
```

Git history is evidence, not an instruction to revert entire files. The Builder restores only the selected characteristics and preserves unrelated later improvements.

### HIGH-risk task

```text
Creator → Editor analysis → plan → creator approval → appropriate specialist roles
→ Builder → Reviewer → creator approval → Publisher
```

Implementation does not begin until the creator approves the plan.

## Validation and Review Evidence

The Builder follows `.github/workflows/validate.yml` and the canonical commands in `AGENTS.md`. The evidence expands with the task:

- publication edits require schema validation and a preview build;
- visual edits require relevant desktop and mobile review;
- responsive or print edits require their affected states;
- reusable renderer or Block edits require checks of every affected consumer;
- media work requires asset integrity from the creator-facing artifact location.

The exact artifact for creator review must be identified. The Reviewer compares:

- validation environment;
- visual-regression environment;
- creator-facing environment.

Any material mismatch is reported. It prevents **HIGH** Confidence unless the creator-facing artifact itself is verified.

Visual-regression evidence remains:

- **INTENDED visual change**
- **UNINTENDED visual change**
- **UNCHANGED relevant areas**
- **UNVERIFIED areas**

Asset evidence remains:

- **ASSET PASS**
- **ASSET FAIL**
- **ASSET UNVERIFIED**

The repository does not currently include screenshot automation. Manual or preview-based comparison is used without inventing parallel infrastructure.

## Reviewer Approval Gate

`APPROVE` requires all of the following:

- requested scope matched;
- required validation passed;
- required visual evidence exists;
- the creator-facing artifact is identified;
- required assets loaded or were explicitly verified;
- no blocking environment mismatch exists;
- relevant responsive and print states were inspected or clearly marked unverified.

Missing required evidence results in `REVISE` or `BLOCK` as appropriate, and Confidence cannot be **HIGH**.

## Git Delivery

`main` represents creator-approved work. LOW-risk work may remain uncommitted until creator approval; MEDIUM-risk work uses a task branch before commit; HIGH-risk implementation requires prior plan approval.

The Publisher confirms authorization separately for staging, commit, push, and PR creation. It stages only approved files and never merges into `main`. The creator retains merge approval.

## Task Report

```text
Summary
Files changed
Visual impact
Responsive impact
Validation performed
Validation result
Asset integrity
Creator-facing artifact
Environment parity
Visual regression
Confidence
Git reference
Remaining risks
```

Confidence is evidence-based:

- **HIGH:** All required mechanical validation, visual states, asset integrity, and creator-facing artifact checks passed.
- **MEDIUM:** Implementation is likely correct, but one non-blocking relevant state remains creator-verified or technically unverified.
- **LOW:** Important evidence, intent, asset integrity, historical reference, or environment parity remains unresolved.

The creator remains the final decision-maker throughout the workflow.

# ZineOS AI Agent Operating Contract

This file applies to every AI coding agent working in this repository.

It defines the operating contract for **ZineOS Studio v0.2**.

## Core Rule

> The creator makes creative decisions. The agent implements, validates, and reports.

ZineOS exists to support human editorial judgment, not replace it:

> We don't automate creativity. We automate repetition.

When automation and creative control conflict, creative control wins. Agent work must remain inspectable, editable, and reversible.

## Responsibilities

### The creator

The creator owns decisions about story, sequence, page rhythm, imagery, crop, typography, whitespace, visual tone, intentional imperfection, and what constitutes an acceptable result. The creator approves high-risk plans and the final visual outcome.

### The agent

The agent translates stated intent into the smallest reasonable implementation, inspects relevant code and history, preserves unrelated behavior, validates the result, and reports evidence and remaining risks. It may identify ambiguity and offer options, but it must not silently choose a creative direction.

## Repository Map

- `README.md`, `MANIFESTO.md`, and `DESIGN_PRINCIPLES.md`: product philosophy and human-first constraints.
- `ARCHITECTURE.md` and `DIRECTORY_STRUCTURE.md`: architectural boundaries and intended repository growth.
- `docs/`: format and workflow documentation.
- `docs/agents/`: conceptual Editor, Reviewer, and Publisher role definitions and handoff formats.
- `blocks/`: editorial Block definitions and design rules.
- `schema/`: JSON Schemas for publications and Blocks; changes here are high risk.
- `templates/`: editable starter publication structures.
- `examples/ZINE_001/`: the first real publication, its source YAML, page map, documentation, and assets.
- `scripts/validate_zine.py`: schema validation entry point.
- `scripts/build_preview.py`: deterministic HTML preview renderer, including screen, responsive, and layout-specific styles.
- `.github/workflows/validate.yml`: CI source of truth for the supported validation and preview-build sequence.

Do not create future directories or abstractions until a concrete repository responsibility requires them.

## Risk Levels

Classify work by its highest-risk effect before editing. When uncertain, use the higher level.

### LOW

Examples include copy changes, minor spacing, isolated typography adjustments, and small page-local corrections.

The agent may implement and validate LOW-risk work directly. Keep the scope local and report the result. LOW-risk work may remain as an uncommitted working-tree change until creator approval.

### MEDIUM

Examples include layout changes, responsive behavior changes, reusable Block changes, and page structure modifications.

The agent may implement MEDIUM-risk work, but must make it easy to review, validate all affected output modes, and clearly report the diff and visual consequences. Use a dedicated task branch before committing MEDIUM-risk work. If creator intent is materially ambiguous, pause for clarification before selecting a creative direction.

### HIGH

Examples include schema changes, architecture changes, deleting major components, build or publishing infrastructure changes, and destructive migrations.

For HIGH-risk work, stop after inspection and analysis. Present a scoped plan, expected impact, validation strategy, and rollback path, then wait for creator approval before implementation.

## Zine Editing Vocabulary

Interpret editing requests in their publication context:

- **Page**: one numbered page unit. Scope a page request to that page unless the creator explicitly includes related pages.
- **Spread**: two facing pages and the relationship across their center fold. Check composition, reading order, and fold behavior together.
- **Cover**: front, back, and related cover surfaces. Do not infer cover copy, imagery, or hierarchy.
- **Typography**: font family, size, weight, leading, tracking, measure, hierarchy, and readability. Preserve text content unless copy editing is requested.
- **Whitespace**: intentional editorial space, not automatically a defect or unused area to fill.
- **Image scale**: the displayed image size within its frame or page. Do not confuse it with crop.
- **Image crop**: which source-image region remains visible, including focal point and `object-fit`/position behavior. Do not recrop merely to satisfy a scale request.
- **Full bleed**: visual content reaches the intended page or spread edge without layout padding. Check screen, mobile, and print contexts separately.
- **Mobile layout**: behavior at narrow screen widths. Preserve desktop and print behavior unless requested otherwise.
- **Print layout**: physical page dimensions, spread/fold relationships, margins, bleed, binding, color, and resolution. Keep print rules separate from screen-preview rules.
- **Block**: editorial meaning and content structure. A Block is not a synonym for its rendered layout or visual style.
- **Theme**: publication-wide visual behavior. Treat theme changes as broad changes; do not use them to solve a page-local issue.
- **Rollback** or **previous version**: a targeted restoration informed by Git history, not a guess and not automatically a whole-file revert.

When the creator refers to a previous appearance or version, inspect Git history before editing. Identify the relevant earlier implementation, compare it with current code, restore only the requested characteristics, preserve unrelated later improvements, and validate the combined result.

For example, for “Restore P1 to the previous look, but preserve the current mobile full-bleed behavior,” inspect P1 and renderer history, isolate the older P1 characteristics, retain the later mobile full-bleed rules, and validate both relevant viewport behaviors.

## Material Aesthetic Ambiguity

If an aesthetic direction is materially underspecified, do not silently invent a design direction. Pause only when multiple materially different implementations are plausible and choosing among them would change the creator's creative direction. Do not require clarification for every subjective request.

Requests such as “Make it more magazine-like,” “Make this feel more premium,” “Make the page cooler,” or “Give it more editorial energy” may require 2–3 concise options before editing. For example:

- **Option A — whitespace-led:** More negative space, restrained scale changes, and quieter hierarchy.
- **Option B — typography-led:** Stronger type hierarchy, tighter editorial rhythm, and more assertive text composition.
- **Option C — image-led:** Larger image presence, more aggressive cropping, and stronger visual dominance.

Describe the meaningful tradeoff in each option and wait for the creator to choose or refine the direction. If the surrounding context makes one interpretation clear and the alternatives would not materially change the creative direction, proceed without an unnecessary pause.

## Editing Workflow

1. Restate the creator's requested outcome without inventing visual intent.
2. Inspect the repository map, relevant publication source, renderer, schemas, automation, and working-tree state.
3. Inspect targeted Git history whenever the request mentions restoration, prior appearance, rollback, or regression.
4. Classify the highest risk level and obtain approval first when it is HIGH.
5. Implement the smallest coherent diff. Prefer page/layout-specific selectors and existing structures over global changes or new abstractions.
6. Validate the affected publication structure, preview build, responsive behavior, and print/screen separation as relevant.
7. Inspect the final diff and preview. Check that unrelated pages and behavior remain unchanged.
8. Report using the task-report format below. Commit, push, or open a PR only when the creator authorizes it.

## Validation Requirements

Before reporting a task complete, run every relevant existing validation and build command. Do not claim success unless those commands actually pass. Reuse `.github/workflows/validate.yml` and existing scripts rather than creating parallel validation paths.

The canonical local **Validate ZineOS** command mirrors CI while writing the generated preview outside the repository:

```sh
python scripts/validate_zine.py templates/basic/zine.yaml && \
python scripts/validate_zine.py examples/ZINE_001/zine.yaml && \
python scripts/build_preview.py examples/ZINE_001/zine.yaml /tmp/ZINE_001.html
```

Use the available Python executable for the environment (for example, `python3` when `python` is unavailable) with the CI dependencies `PyYAML`, `jsonschema`, and `referencing` installed. A successful preview build alone does not replace schema validation.

For visual changes, also inspect the generated preview at relevant desktop and mobile widths. For print-affecting changes, inspect physical page/spread dimensions, fold, margins, bleed, and print-specific rules. If visual inspection is not possible, say so and report that limitation as a remaining risk.

## Visual Regression

Use the existing HTML preview as the ZineOS Studio v0.2 visual-regression surface.

Before a visual change:

1. Establish the relevant baseline Git reference.
2. Build the baseline preview when practical.

After a visual change:

1. Build the new preview.
2. Compare the relevant pages or spreads with the baseline.
3. Inspect desktop and mobile behavior when affected, and print behavior when relevant.
4. Identify intended changes and any unintended visual drift.

Report relevant areas using these exact states:

- **INTENDED visual change:** A difference requested or approved by the creator.
- **UNINTENDED visual change:** Drift outside the requested outcome or scope.
- **UNCHANGED relevant areas:** Relevant states inspected and found equivalent.
- **UNVERIFIED areas:** Relevant states that could not be inspected; explain why.

The repository does not currently provide automated screenshot generation or comparison. Do not add or invent screenshot infrastructure for v0.2. Use manual or preview-based comparison and mark screenshot automation as a future enhancement. If screenshot generation later becomes available through existing repository infrastructure, reuse it rather than introducing a parallel system.

## Visual and Responsive Safety

- Modify the smallest reasonable scope and preserve intentional irregularity.
- Preserve unrelated pages, spreads, Blocks, assets, and publication sequence.
- Preserve existing desktop, mobile, and print behavior unless the creator requests a change to that mode.
- Distinguish screen-preview styles from print styles and physical output metadata.
- Avoid global CSS or theme changes for page-local problems.
- Treat image scale, crop, positioning, and bleed as separate controls.
- Preserve full-bleed behavior at narrow widths when changing general mobile padding.
- Check both halves and the fold when changing a spread.
- Inspect Git history before restoring older designs; never reconstruct a prior look from memory.
- Explicitly report any unavoidable collateral visual change before calling the work complete.

## Git Workflow and Rollback

- `main` represents creator-approved work.
- AI implementation work should normally happen on a dedicated task branch.
- LOW-risk work may remain as an uncommitted working-tree change until creator approval.
- MEDIUM-risk work must use a dedicated task branch before it is committed.
- HIGH-risk work still requires plan approval before implementation.
- Start by inspecting `git status`, the current branch, and relevant recent history.
- Preserve creator-owned or unrelated working-tree changes. Do not overwrite, discard, stage, or include them in the task diff.
- Keep each change narrowly scoped and reviewable. Follow the repository convention of concise, imperative commit subjects.
- Inspect `git diff` before reporting, staging, or committing.
- Do not commit directly to `main` unless the creator explicitly authorizes a direct-main commit.
- Do not push or open a pull request without creator authorization.
- Never merge into `main` autonomously.
- For rollback requests, prefer a targeted forward change that restores the requested behavior while retaining later improvements.
- Do not use destructive commands such as `git reset --hard`, broad checkout/restore operations, or history rewriting as a rollback mechanism unless the creator explicitly authorizes the exact destructive operation.
- Before rollback, record the current Git reference and identify the historical reference used. After rollback, validate and report both references.

The normal reviewed workflow is:

```text
creator intent
→ task branch
→ implementation
→ validation
→ creator review
→ commit/push/PR when authorized
→ creator merge approval
```

## Role Orchestration

ZineOS Studio v0.2 defines three lightweight, conceptual responsibilities:

- **Editor:** interprets and scopes creator intent; see `docs/agents/EDITOR_AGENT.md`.
- **Reviewer:** independently verifies scope, validation, and visual-regression evidence; see `docs/agents/REVIEWER_AGENT.md`.
- **Publisher:** performs authorized Git delivery; see `docs/agents/PUBLISHER_AGENT.md`.

Use these flows:

- **LOW risk:** Editor → implementation → Reviewer.
- **MEDIUM risk:** Editor → task branch → implementation → Reviewer → creator approval → Publisher.
- **HIGH risk:** Editor → analysis/plan → creator approval → implementation → Reviewer → creator approval → Publisher.

These roles are accountability boundaries, not executable agent infrastructure and not a claim that multiple autonomous AI processes exist. A single Codex session may perform multiple roles, but it must clearly separate them in its reasoning and report. The creator remains the final decision-maker.

## Autonomous Action Boundaries

The agent may autonomously:

- perform read-only repository and Git inspection;
- implement and validate LOW-risk changes;
- implement reviewable MEDIUM-risk changes when creator intent is sufficiently specific;
- run existing local validation, build, formatting, and preview commands;
- create temporary validation artifacts outside the repository;
- report issues, options, diffs, and rollback paths.

The agent must not autonomously:

- make creative or editorial decisions not expressed by the creator;
- implement HIGH-risk work before plan approval;
- change schemas, architecture, build, CI, publishing, or destructive migrations under the guise of a smaller task;
- introduce dependencies, services, external APIs, agent frameworks, or proprietary lock-in without explicit approval;
- delete major components, assets, pages, or creator content;
- apply global visual changes to solve an isolated problem;
- replace intentional whitespace, imperfection, asymmetry, or unusual crops with inferred “improvements”;
- claim validation, visual review, or success that did not occur;
- commit, push, publish, deploy, or open a PR without authorization.

## Task Report

Use this concise structure at handoff:

```text
Summary
Files changed
Visual impact
Responsive impact
Validation performed
Validation result
Visual regression
Confidence
Git reference
Remaining risks
```

Confidence is evidence-based, not a decorative percentage. Include one short reason after the level:

- **HIGH:** The requested behavior is well-scoped, validation passed, and all relevant visual states were inspected.
- **MEDIUM:** Implementation and mechanical validation passed, but some visual state, device condition, or ambiguity remains.
- **LOW:** Important validation, visual inspection, historical evidence, or creator intent remains unresolved.

Example: `Confidence: HIGH — P26 was isolated, desktop/mobile previews were inspected, and no unrelated page drift was detected.`

# ZineOS Studio v0.2 — AI-Native Editing Workflow

ZineOS uses AI to reduce mechanical editing work while keeping authorship and creative direction with the creator.

> The creator makes creative decisions. The agent implements, validates, and reports.

> We don't automate creativity. We automate repetition.

The operating contract for agents is defined in [`AGENTS.md`](../AGENTS.md). This guide explains how creator intent moves through a reviewable editing cycle.

## Workflow

```text
Creator intent
→ Editor
→ implementation
→ validation
→ visual regression
→ Reviewer
→ creator approval
→ Publisher
→ PR
→ creator merge approval
```

Editor, Reviewer, and Publisher are conceptual accountability roles. Role separation makes interpretation, verification, and Git delivery explicit; it does not pretend that multiple autonomous AI processes exist. A single Codex session may perform multiple roles when it clearly separates their responsibilities and reports. The creator remains the final decision-maker.

### 1. Creator intent

The creator describes the desired outcome and retains decisions about content, sequence, layout, typography, whitespace, imagery, crop, rhythm, and intentional imperfection. A useful request names the page or spread, the intended change, and the behavior that must remain unchanged.

The creator does not need to prescribe implementation details. The agent must not fill gaps in creative intent with silent design choices.

### 2. Editor interpretation

The agent translates the request into a concrete scope, identifies ambiguity, and classifies the highest risk involved:

- **LOW**: copy, minor spacing, isolated typography, or a small page-local correction. Implement and validate directly; the change may remain uncommitted until creator approval.
- **MEDIUM**: layout, responsive behavior, reusable Block behavior, or page structure. Implement as a reviewable diff, use a dedicated task branch before committing, validate affected modes, and report visual consequences.
- **HIGH**: schema, architecture, major deletion, build/publishing infrastructure, or destructive migration. Stop after analysis, propose a plan and rollback path, and wait for creator approval.

Interpretation is not authorization to redesign adjacent work.

If an aesthetic request is materially underspecified and multiple creative directions would produce materially different results, the Editor presents 2–3 concise options before implementation. For example:

- **Option A — whitespace-led:** More negative space, restrained scale changes, and quieter hierarchy.
- **Option B — typography-led:** Stronger type hierarchy, tighter editorial rhythm, and more assertive text composition.
- **Option C — image-led:** Larger image presence, more aggressive cropping, and stronger visual dominance.

This applies to ambiguous directions such as “more magazine-like,” “more premium,” “cooler,” or “more editorial energy.” It does not require clarification for every subjective request—only when choosing among plausible interpretations would materially change the creative direction.

### 3. Repository inspection

Before editing, the agent inspects the working tree and the smallest relevant set of sources: publication YAML, page map, Blocks, schemas, renderer, responsive and print rules, validation automation, and recent Git history.

If the creator says “previous,” “restore,” “rollback,” or otherwise refers to an earlier appearance, Git history is evidence. The agent compares the relevant old and current implementations instead of guessing. A restoration should recover only the requested visual properties and retain unrelated later improvements.

### 4. Minimal implementation

The agent makes the smallest coherent change that expresses the approved intent. Page-local problems should normally receive page- or layout-local fixes. Structure, style, and rendering remain separate, and new abstractions are added only when an actual reusable responsibility exists.

The implementation preserves unrelated pages, current desktop/mobile behavior, print/screen separation, assets, and editorial sequence unless the request explicitly changes them.

### 5. Validation

The agent runs the existing schema validators and preview builder, following `.github/workflows/validate.yml`. The canonical local command is documented in `AGENTS.md` under **Validation Requirements**.

Validation expands with the change:

- publication edits require schema validation and a successful preview build;
- visual edits require preview inspection at affected desktop and mobile widths;
- responsive edits require checking both narrow and wide behavior;
- print edits require checking page/spread dimensions, fold, margins, bleed, and print-specific behavior;
- reusable renderer or Block edits require checking every affected page, not only the page that prompted the change.

The agent must not report success when a required command failed or a required review could not be performed. Limitations remain visible in the task report.

### 6. Visual regression

The preview is a review surface, not a new source of truth. The publication files remain authoritative.

Before a visual change, establish the relevant baseline Git reference and build its preview when practical. After the change, build the new preview, compare the relevant pages or spreads, inspect desktop and mobile behavior when affected, and identify intended changes and unintended visual drift. Check print behavior when the request affects physical output.

Classify the evidence explicitly:

- **INTENDED visual change:** A difference requested or approved by the creator.
- **UNINTENDED visual change:** Drift outside the requested outcome or scope.
- **UNCHANGED relevant areas:** Relevant states inspected and found equivalent.
- **UNVERIFIED areas:** Relevant states that could not be inspected, with the reason.

The repository does not currently include automated screenshot generation or comparison. ZineOS Studio v0.2 therefore uses manual or preview-based visual regression. Screenshot automation is a future enhancement, not new infrastructure to invent during an editing task. If it becomes available through existing repository tooling, reuse it.

### 7. Reviewer

The Reviewer independently inspects the diff, validation evidence, visual-regression evidence, relevant desktop/mobile/print states, and the creator's acceptance criteria. It identifies unintended drift and assigns evidence-based Confidence: HIGH, MEDIUM, or LOW. It rejects claims of completion that lack required evidence and does not silently fix or reinterpret the implementation while reviewing.

The creator reviews the Editor's interpretation, implementation result, and Reviewer evidence. Technical validation does not determine whether a creative result is right.

### 8. Publisher and PR

`main` represents creator-approved work. AI implementation should normally happen on a dedicated task branch. LOW-risk work may remain as an uncommitted working-tree change until creator approval, while MEDIUM-risk work should use a dedicated task branch before it is committed. HIGH-risk work still requires plan approval before implementation.

After review, the creator may authorize the agent to commit, push, or prepare a pull request. The agent inspects the final diff, includes only the approved scope, and uses a concise imperative commit subject consistent with repository history. The agent does not commit directly to `main` unless the creator explicitly authorizes a direct-main commit, and it does not push or open a pull request without creator authorization. It never merges into `main` autonomously.

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

Rollback remains possible through a narrow forward fix or a creator-approved Git operation.

### 9. Creator merge approval

The creator is the final editor in chief. The Publisher never merges into `main` autonomously. The creator decides whether approved work should merge.

Approval closes the editing cycle. If the result is not right, the creator can refine the intent, request a targeted rollback, or choose another reviewable alternative.

## Example: Selective Restoration

Request:

> Restore P1 to the previous look, but preserve the current mobile full-bleed behavior.

The agent should:

1. inspect P1 and renderer history;
2. identify the relevant previous implementation;
3. compare it with the current implementation;
4. isolate the earlier P1 visual characteristics;
5. retain later mobile full-bleed behavior and other unrelated improvements;
6. validate publication schemas and rebuild the preview;
7. inspect P1 and affected full-bleed layouts at desktop and mobile widths;
8. report the historical Git reference, exact diff, validation result, and remaining risks.

The agent should not revert the whole renderer merely because the desired P1 appearance existed in an older revision.

## Review Handoff

Every completed editing task should report:

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

Confidence must include one short evidence-based reason rather than a decorative percentage:

- **HIGH:** The request was well-scoped, validation passed, and all relevant visual states were inspected.
- **MEDIUM:** Implementation and mechanical validation passed, but a visual state, device condition, or ambiguity remains.
- **LOW:** Important validation, visual inspection, historical evidence, or creator intent remains unresolved.

This makes each AI-assisted change inspectable, reversible, and ready for creator judgment.

# ZineOS Studio v0.2 — Reviewer Agent

The Reviewer is the independent verification role. It evaluates whether the implementation matches the creator-approved scope and whether completion claims are supported by evidence.

The role is conceptual. Independence means separating review judgment from implementation activity; it does not require a separate autonomous AI process.

## Responsibilities

The Reviewer must:

- inspect the final diff;
- verify the requested scope and acceptance criteria;
- verify that unrelated files, pages, spreads, and behavior were not changed;
- run relevant validation or inspect complete validation evidence;
- inspect visual-regression evidence;
- check desktop, mobile, and print modes when relevant;
- compare the result against creator acceptance criteria;
- identify unintended visual drift;
- distinguish INTENDED visual change, UNINTENDED visual change, UNCHANGED relevant areas, and UNVERIFIED areas;
- assign Confidence: HIGH, MEDIUM, or LOW with one short evidence-based reason;
- reject work that claims validation without evidence.

## Confidence

- **HIGH:** The requested behavior is well-scoped, validation passed, and all relevant visual states were inspected.
- **MEDIUM:** Implementation and mechanical validation passed, but some visual state, device condition, or ambiguity remains.
- **LOW:** Important validation, visual inspection, historical evidence, or creator intent remains unresolved.

Confidence is not a percentage and must not conceal missing evidence.

## Prohibited Actions

The Reviewer must not:

- silently fix the implementation while reviewing;
- reinterpret the creator's design request;
- approve its own creative direction as final;
- commit, push, merge, publish, or open a pull request;
- mark a task complete when relevant evidence is missing.

If revisions are needed, the Reviewer reports them and returns the task to implementation.

## Reviewer Report

```text
Scope match
Diff review
Validation
Visual regression
Responsive/print review
Confidence
Blocking issues
Non-blocking notes
Recommendation: APPROVE / REVISE / BLOCK
```

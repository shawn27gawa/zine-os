# ZineOS

> An open source operating system for independent publishing.

ZineOS is an open source project for designing, editing, and publishing independent zines.

It aims to make zine creation more accessible without replacing the creative decisions of the creator.

## Philosophy

**We don't automate creativity. We automate repetition.**

Creators make the decisions.  
ZineOS helps with the mechanics.

## Project Status

**ZineOS v1 Release Candidate**

The repository now provides a repeatable path from a neutral photo inbox to an
editable publication source, creator-facing Preview and Studio, validated
review release, and A5 saddle-stitch print output. ZINE_001 remains the complete
creator-approved example; a generic non-ZINE_001 integration fixture prevents
the core workflow from depending on that publication's content or paths.

Start with the [Quick Start](docs/QUICK_START.md), then run the canonical local
validation command:

```sh
python3 scripts/validate_zineos.py
```

New publications start from a neutral project rather than copying ZINE_001.
See [Project and Inbox Bootstrap](docs/PROJECT_BOOTSTRAP.md) for the dry-run-first
workflow that inventories original photographs without selecting or modifying them.

Build a validated creator-review artifact set with one command:

```sh
python scripts/release_zine.py path/to/zine.yaml --mode review
```

See [One-command Release](docs/RELEASE_WORKFLOW.md) for immutable output and
formal CMYK print requirements.

See [docs/V1_ROADMAP.md](docs/V1_ROADMAP.md) for the v1 completion criteria.

## Core Ideas

- Human-first creative workflow
- Open and editable formats
- Block-based editorial design
- Markdown-friendly
- Print-first
- AI-assisted, not AI-controlled
- No dependency on proprietary software
- Designed for independent publishing

## Roadmap

### Phase 0 — Foundation
- README
- Manifesto
- Design Principles
- Project structure
- License

### Phase 1 — Core
- Zine schema
- Block Library
- Templates
- Example Zine

### Phase 2 — Intelligence
- Curator
- Editor
- Art Director
- Reviewer

### Phase 3 — Preview
- Browser preview
- Spread view
- Print simulation

### Phase 4 — Integrations
- Figma workflow
- Obsidian workflow
- PDF export
- Plugins

---

Everything remains editable.

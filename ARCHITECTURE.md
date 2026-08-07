# ZineOS Architecture

This document describes the high-level architecture of ZineOS.

ZineOS separates the creative process into small, understandable layers.

The goal is to keep the system modular, editable, and independent from any single application or AI model.

---

## Overview

```mermaid
flowchart TD

    A[Creator]
    B[Project Files]
    C[Asset Library]
    D[Block Library]
    E[Editorial Engine]
    F[Layout Composer]
    G[Renderer]
    H[Preview]
    I[Export]
    J[External Tools]

    A --> B
    A --> C

    B --> E
    C --> E
    D --> E

    E --> F
    F --> G
    G --> H
    G --> I

    J <--> B
    J <--> G

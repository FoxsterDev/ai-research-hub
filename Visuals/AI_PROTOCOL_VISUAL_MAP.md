# AI Protocol Visual Map

## Purpose
This file gives a generic visual overview of the public `AIRoot` protocol model.

It focuses on:
- the public `xuunity` core
- optional host-local overlays
- project-local memory and outputs

It is a navigation aid, not the source of truth.

## 1. Protocol Families

```mermaid
flowchart LR
    A[Repo Router\nAgents.md] --> B[XUUnity]
    A --> C[Optional Host-Local Protocols]

    B --> B1[Engineering Work]
    B --> B2[Product Protocols]
    B --> B3[System Utilities]
    B --> B4[Skills]

    C --> C1[Private Host Flows]
    C --> C2[Monorepo Helpers]
    C --> C3[Private Architecture or Survey Layers]
```

## 2. Load Order

```mermaid
flowchart TD
    A[Repo Agents.md] --> B[Public XUUnity Core\nAIRoot/Modules/XUUnity/]
    B --> C[Optional Host-Local Overlays\nAIModules/ when attached]
    C --> D[Project Agents.md]
    D --> E[ProjectMemory\nAssets/AIOutput/ProjectMemory/]
    E --> F[Previous Outputs\nAssets/AIOutput/]
```

## 3. XUUnity Main Stack

```mermaid
flowchart TD
    A[User Command\nxuunity ...] --> B[Start Session Routing]
    B --> C[Primary Role]
    C --> D[Code Style]
    D --> E[Task File]
    E --> F[Core Skills]
    F --> G[Matched Skill Families]
    G --> H[Reviews or Utilities]
    H --> I[Platform Overlay if needed]
    I --> J[Optional Host Overlay if relevant]
    J --> K[Project Memory]
    K --> L[Relevant Prior Outputs]
```

## 4. Knowledge Flow

```mermaid
flowchart TD
    A[New Knowledge] --> B[Extract]
    B --> C[Intake Review]
    C --> D{Decision}
    D -->|public-safe reusable| E[Public Core\nAIRoot/Modules/XUUnity/]
    D -->|host-local reusable| F[AIModules/]
    D -->|project-specific| G[ProjectMemory or SkillOverrides]
    D -->|report or draft| H[Assets/AIOutput/]
    D -->|reject| I[No Action]
```

## 5. Storage Boundaries

```mermaid
flowchart LR
    A[AIRoot] --> A1[Public reusable modules]
    A --> A2[Public setup and templates]
    B[AIModules] --> B1[Optional host-local overlays]
    C[AIOutput] --> C1[Host-local mutable state]
    D[ProjectMemory] --> D1[Project-local durable truth]
    E[Project Outputs] --> E1[Project-local reports and drafts]
```

## 6. Quick Routing Guide

| Need | Route |
| --- | --- |
| Fix or refactor code | `xuunity ...` |
| Review SDK or native integration | `xuunity sdk ...` or `xuunity native ...` |
| Ask product-facing implementation question | `xuunity product ...` |
| Audit project readiness | `xuunity product health ...` |
| Check project-memory freshness | `xuunity project memory freshness ...` |
| Extract reusable knowledge | `xuunity extract knowledge` |
| Convert a long chat into reusable engineering context | `xuunity system extract review artifact from this chat` |
| Use private host-local flows | host-specific protocol selected by the host router |

## 7. Main Rule

Public `AIRoot` documents:
- `xuunity`
- generic optional host-local overlays

Private host-only protocol families should be documented only in host-local routers and host-local docs.

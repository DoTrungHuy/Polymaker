# PolyPilot competition proposal

PolyPilot is an explainable AI material advisor for the Polymaker challenge in the 2026 Feishu AI Future Talent program.

## Goal

Turn ambiguous natural-language 3D-printing requirements into a traceable Top-3 material comparison, print settings, post-processing guidance, explicit exclusions, and human-escalation warnings.

## MVP

- 12 representative Polymaker materials with structured official-source facts.
- 30 fixed evaluation scenarios.
- React web workbench and FastAPI decision service.
- Feishu Aily intent extraction, bot Card 2.0 result, and Bitable feedback/audit trail.
- Deterministic fallback when Aily is unavailable.

## Differentiation

The language model does not own the recommendation. It extracts intent; versioned evidence and hard rules own compatibility and ranking. Missing, conflicting, or unreviewed fields never become implicit passes.

## Delivery

The public repository is named `Polymaker`; the product remains `PolyPilot`. Code, structured facts, tests, setup instructions, deployment configuration and demo script ship in one repository. Source PDFs and private registration documents are not tracked.

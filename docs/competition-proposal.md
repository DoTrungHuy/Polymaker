# PolyPilot competition proposal

PolyPilot is an explainable AI material advisor for the Polymaker challenge in the 2026 Feishu AI Future Talent program.

## Goal

Turn ambiguous natural-language 3D-printing requirements into a traceable Top-3 material decision, then retain the decision, evidence, version and feedback as a reusable Polymaker-facing asset.

## Relationship to the official Polymaker Web App

The official Web App already supports use-case discovery, material comparison, print-condition filtering, shareable comparison views, AI assistance and hundreds of slicer profiles. PolyPilot does not compete with or reproduce those strengths. It explores the next organizational layer: auditable hard-constraint decisions, counterfactual explanations and a Feishu-native feedback trail for technical support, resellers and product teams.

## MVP

- 12 representative Polymaker materials with structured official-source facts.
- 30 fixed evaluation scenarios.
- React web workbench and FastAPI decision service.
- Feishu Aily intent extraction, bot Card 2.0 result, and Bitable feedback/audit trail.
- Deterministic fallback when Aily is unavailable.

## Differentiation

The language model does not own the recommendation. It extracts intent; versioned evidence and hard rules own compatibility and ranking. Missing, conflicting, or unreviewed fields never become implicit passes.

The counterfactual decision lab also explains why a named material was excluded and computes the smallest explicit condition changes needed for it to enter the candidate set. Evidence gaps and safety escalation can never be bypassed by changing user settings.

Feishu is part of the product mechanism rather than a presentation channel: Aily extracts intent, Card 2.0 supports evidence and correction actions, and Bitable stores versioned requests, outcomes and feedback for audit and calibration.

## Business value hypotheses

- Reduce repeated material-selection work and avoidable print failures by converting common scenarios into reusable decisions.
- Give resellers and technical-support teams a consistent recommendation record with explicit conditions and evidence.
- Feed aggregated scenario-material-feedback patterns back into support content and product portfolio decisions.
- Treat a 30-60 minute manual comparison as a pilot hypothesis, not a proven baseline; target a decision flow under five minutes and measure the actual baseline during external testing.

## Verified implementation baseline

- 12 approved representative materials with field-level official sources.
- 30 fixed regression scenarios with a current 30/30 local benchmark result.
- 23 backend tests plus frontend test, type-check and production build.
- React result comparison, exclusion trace and counterfactual decision lab.
- FastAPI v1 API, Feishu adapters, Vercel routing and GitHub Actions.

The fixed benchmark measures deterministic regression consistency, not independent expert accuracy or product safety certification.

## Delivery

The public repository is named `Polymaker`; the product remains `PolyPilot`. Code, structured facts, tests, setup instructions, deployment configuration and demo script ship in one repository. Source PDFs and private registration documents are not tracked.

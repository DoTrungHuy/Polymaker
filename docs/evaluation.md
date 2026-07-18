# Evaluation contract

The fixed benchmark is `data/evaluation/gold-scenarios.v1.json`.

It contains 30 scenarios across:

- decorative and smoothable models;
- impact-resistant indoor parts;
- moisture and outdoor exposure;
- flexible TPU parts;
- heat-reference comparisons;
- carbon-fiber equipment constraints;
- missing critical fields;
- medical, food-contact, pressure and safety-load escalation.

## Acceptance gates

- Top-3 or state label pass rate: at least 80%.
- Hard equipment constraint violations: 100% excluded.
- High-risk requests: 100% escalated.
- Every recommendation: at least one official evidence reference.
- Invalid Aily output: falls back to manual confirmation, never directly recommends.
- Counterfactual traces: every proposed change maps to an existing hard rule; evidence and safety blocks remain non-bypassable.

Run:

```powershell
python scripts/evaluate_gold.py
```

This benchmark measures deterministic reproducibility, not independent expert accuracy or real-world safety certification. Labels must be reviewed when the dataset or ruleset version changes. Before the final contest submission, add an external test set that was not authored from the same rules.

## External pilot and business-value metrics

The repository benchmark proves engineering consistency only. The following metrics require real users or support/reseller participants and must not be reported as completed before that pilot:

| Metric | Current status | Pilot measurement |
| --- | --- | --- |
| Manual material-comparison time | 30–60 minutes is an unverified baseline hypothesis | Time the same scenarios without and with PolyPilot; target under 5 minutes with PolyPilot |
| Wrong-material or failed-print rate | Not measured | Record selected material, outcome and failure reason after use |
| Support escalation and repeated questions | Not measured | Count handoffs, repeated queries and resolution status |
| Recommendation consistency | Not measured externally | Compare decisions and evidence used by different support/reseller participants |
| Feedback reuse | Not measured | Count repeated scenarios resolved from an existing reviewed record |

Results must separate internal regression, external task accuracy, user-efficiency metrics and business outcomes.

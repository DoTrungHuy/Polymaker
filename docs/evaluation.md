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

Run:

```powershell
python scripts/evaluate_gold.py
```

This benchmark measures deterministic reproducibility, not real-world safety certification. Labels must be reviewed when the dataset or ruleset version changes.

# PolyPilot data governance

## Review states

| State | May affect recommendation? | Meaning |
| --- | --- | --- |
| `approved` | Yes | Official source, applicability and access date reviewed |
| `review_pending` | No | Collected but not yet reviewed |
| `conflicting` | No | Sources disagree or applicability is unclear |
| `demo_only` | No | Synthetic test fixture only |

## Field-level evidence

Every field that can affect a hard exclusion must map to a `SourceRef`. The minimum protected fields are nozzle range, bed range and enclosure requirement. Abrasive materials must also evidence the hardened-nozzle requirement; thermal filtering must evidence a named heat-reference method.

Unknown values remain unknown. They are never converted to zero, false, or a positive match.

## Thermal data

HDT, glass transition, Vicat softening and heat stability are different measurements. PolyPilot stores `heat_reference_type` beside every numeric value and repeats the caveat in the recommendation. The value is a comparison aid, not a safe service-temperature specification for a printed part.

## Copyright and change control

The public repository stores links and structured facts, not copied source PDFs. Any source refresh changes the dataset version, reruns data validation and the 30-scenario benchmark, and requires a human review before release.

## Feedback and business-learning data

External-pilot records separate the user's scenario, decision inputs, selected material, result, correction and operator role. Aggregated patterns may support recommendation consistency, support-content improvement and product-portfolio hypotheses, but no individual record is treated as a product fact. Personal data and free-text feedback must be minimized before analysis, and public artifacts use only anonymized summaries.

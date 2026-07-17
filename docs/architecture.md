# Architecture

```mermaid
flowchart LR
  U[React web or Feishu user] --> I[Aily intent parser]
  I -->|validated JSON| P[Pydantic SelectionIntent]
  I -->|timeout or invalid JSON| F[Deterministic parser and manual form]
  F --> P
  P --> R[Safety gate and hard rules]
  D[(Versioned material facts)] --> R
  R --> S[Transparent weighted ranking]
  S --> O[Top 3, exclusions, evidence]
  O --> W[React result comparison]
  O --> C[Feishu Card 2.0]
  O --> A[(Bitable or local SQLite audit)]
```

## Trust boundaries

- The browser never receives Feishu secrets.
- Aily output is untrusted until Pydantic validation succeeds.
- Only `approved` material profiles participate in decisions.
- Unknown thermal evidence is not treated as a pass.
- The deterministic engine is the only component allowed to produce the final ranking.
- Online persistence uses Bitable; local development uses ignored `.local/` SQLite.

## Deployment

Vercel serves `web/dist` and routes `/api/*` to the FastAPI function in `api/index.py`. The decision core is stateless; versioned material data ship with the repository. No Docker or production SQL server is required for v1.

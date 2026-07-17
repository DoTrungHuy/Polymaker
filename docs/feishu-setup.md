# Feishu / Aily setup

The adapter is implemented, but real end-to-end activation requires a competition tenant and user-owned credentials.

## 1. Custom app

Create a Feishu custom app with a bot, then request the minimum permissions for:

- receiving message events;
- replying to messages;
- running the selected Aily skill;
- creating records in the selected Bitable.

Configure the event callback as:

`https://<deployment>/api/integrations/feishu/events`

Configure CardKit actions as:

`https://<deployment>/api/integrations/feishu/card-actions`

The current MVP validates callback verification tokens. Encrypted event payloads intentionally return `501`; keep event encryption disabled until a reviewed decryptor and replay-protection test suite are added.

## 2. Aily Workflow Skill

The skill receives `query` and `text`, and must synchronously return one JSON object matching this output contract:

```json
{
  "purpose": "户外摄像头支架",
  "max_use_temperature_c": 80,
  "outdoor_exposure": true,
  "flexibility_required": false,
  "moisture_exposure": true,
  "impact_priority": 4,
  "stiffness_priority": 3,
  "appearance_priority": false,
  "budget_level": "standard",
  "risk_level": "normal",
  "risk_tags": [],
  "confidence": 0.93
}
```

Prompt constraints:

1. Extract only facts explicitly stated or unambiguously implied.
2. Use `null` for missing optional fields.
3. Never name or recommend a material.
4. Mark medical, food contact, pressure vessel, safety-load and compliance requests as high risk.
5. Return JSON only; no Markdown fence or prose.

The server calls the official synchronous endpoint:

`POST /open-apis/aily/v1/apps/{app_id}/skills/{skill_id}/start`

Invalid output, timeout, missing configuration or token failure switches to deterministic/manual mode.

## 3. Bitable fields

Create one table with these text/boolean fields:

- `Record ID`
- `Type`
- `Request ID`
- `Purpose`
- `State`
- `Top Materials`
- `Ruleset`
- `Dataset`
- `Payload`
- `Helpful`
- `Reason`
- `Selected Material`

## 4. Environment variables

Copy `.env.example` to `.env` locally or configure the values in Vercel. Never paste credentials into issues, commits, screenshots, videos, or chat logs.

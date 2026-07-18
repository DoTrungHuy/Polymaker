import type { DecisionResponse, MaterialDecisionTrace, MaterialProfile, SelectionForm, SelectionIntent } from './types'

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function parseIntent(text: string): Promise<SelectionIntent> {
  return json(await fetch('/api/v1/intent/parse', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  }))
}

function selectionPayload(form: SelectionForm) {
  const numberOrNull = (value: string) => value.trim() === '' ? null : Number(value)
  return {
    purpose: form.purpose,
    max_use_temperature_c: numberOrNull(form.max_use_temperature_c),
    outdoor_exposure: form.outdoor_exposure,
    flexibility_required: form.flexibility_required,
    moisture_exposure: form.moisture_exposure,
    appearance_priority: form.appearance_priority,
    impact_priority: form.impact_priority,
    stiffness_priority: form.stiffness_priority,
    experience_level: form.experience_level,
    budget_level: form.budget_level,
    printer: {
      nozzle_max_c: numberOrNull(form.nozzle_max_c),
      bed_max_c: numberOrNull(form.bed_max_c),
      has_enclosure: form.has_enclosure,
      has_hardened_nozzle: form.has_hardened_nozzle,
      direct_drive: form.direct_drive,
    },
  }
}

export async function recommend(form: SelectionForm): Promise<DecisionResponse> {
  return json(await fetch('/api/v1/recommendations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(selectionPayload(form)),
  }))
}

export async function explainMaterial(materialKey: string, form: SelectionForm): Promise<MaterialDecisionTrace> {
  return json(await fetch(`/api/v1/decision-lab/${materialKey}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(selectionPayload(form)),
  }))
}

export async function getMaterials(): Promise<MaterialProfile[]> {
  return json(await fetch('/api/v1/materials'))
}

export async function sendFeedback(requestId: string, helpful: boolean): Promise<void> {
  await json(await fetch('/api/v1/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ request_id: requestId, helpful }),
  }))
}

export type DecisionState =
  | 'NEED_MORE_INFO'
  | 'RECOMMEND'
  | 'CONDITIONAL'
  | 'NO_COMPATIBLE_MATERIAL'
  | 'REFUSE_OR_ESCALATE'

export interface TemperatureRange { min_c: number; max_c: number }
export interface PrintSettings {
  nozzle_c: TemperatureRange
  bed_c: TemperatureRange
  speed_mm_s?: string
  cooling?: string
  drying?: string
  annealing?: string
}
export interface SourceRef {
  source_id: string
  url: string
  title: string
  document_version?: string
  accessed_at: string
  page_or_section?: string
  applicability: string
}
export interface MaterialProfile {
  key: string
  display_name: string
  series: string
  family: string
  summary: string
  print_settings: PrintSettings
  requires_enclosure: boolean
  requires_hardened_nozzle: boolean
  capabilities: string[]
  print_difficulty: number
  cost_tier: number
  heat_reference_c?: number
  heat_reference_type?: string
  tradeoffs: string[]
  postprocessing: string[]
  evidence_status: string
  source_refs: SourceRef[]
}
export interface Recommendation {
  material_key: string
  material_name: string
  family: string
  fit_score: number
  evidence_confidence: number
  evidence_status: string
  reasons: string[]
  tradeoffs: string[]
  conditions: string[]
  print_settings: PrintSettings
  postprocessing: string[]
  evidence_refs: SourceRef[]
  score_breakdown: Record<string, number>
}
export interface Exclusion { material_key: string; material_name: string; rule_id: string; reason: string }
export interface DecisionResponse {
  request_id: string
  state: DecisionState
  message: string
  next_question?: string
  recommendations: Recommendation[]
  excluded: Exclusion[]
  triggered_rules: string[]
  human_escalation: boolean
  ruleset_version: string
  dataset_version: string
}
export interface SelectionIntent {
  raw_text: string
  purpose: string
  max_use_temperature_c?: number
  outdoor_exposure?: boolean
  flexibility_required?: boolean
  moisture_exposure?: boolean
  appearance_priority?: boolean
  budget_level?: 'economy' | 'standard' | 'premium'
  risk_level: string
  source: 'aily' | 'deterministic' | 'manual'
  confidence: number
  requires_manual_form: boolean
  parser_message?: string
}
export interface SelectionForm {
  purpose: string
  max_use_temperature_c: string
  outdoor_exposure: boolean
  flexibility_required: boolean
  moisture_exposure: boolean
  appearance_priority: boolean
  impact_priority: number
  stiffness_priority: number
  experience_level: 'beginner' | 'intermediate' | 'advanced'
  budget_level: 'economy' | 'standard' | 'premium'
  nozzle_max_c: string
  bed_max_c: string
  has_enclosure: boolean
  has_hardened_nozzle: boolean
  direct_drive: boolean
}

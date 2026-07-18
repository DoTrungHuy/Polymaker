import { expect, test } from '@playwright/test'

test('advisor renders and exposes manual workflow', async ({ page }) => {
  await page.route('**/api/v1/materials', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/intent/parse', route => route.fulfill({ json: {
    raw_text: '户外支架', purpose: '户外支架', outdoor_exposure: true,
    source: 'deterministic', confidence: .55, risk_level: 'normal', requires_manual_form: true,
    parser_message: '安全回退',
  }}))
  await page.goto('/')
  await expect(page.getByText('把“想打印什么”')).toBeVisible()
  await page.getByPlaceholder('例如：我想打印一个放在汽车里的手机支架……').fill('户外支架')
  await page.getByRole('button', { name: '分析需求 →' }).click()
  await expect(page.getByText('结构化确认')).toBeVisible()
})

test('evidence ledger is reachable', async ({ page }) => {
  await page.route('**/api/v1/materials', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await page.getByRole('button', { name: /证据账本/ }).click()
  await expect(page.getByText('每一个硬判断，都能回到来源。')).toBeVisible()
})

test('evaluation view explains measurable quality', async ({ page }) => {
  await page.route('**/api/v1/materials', route => route.fulfill({ json: [] }))
  await page.goto('/')
  await page.getByRole('button', { name: /评测方法/ }).click()
  await expect(page.getByText('不是“看起来聪明”，而是可以被测量。')).toBeVisible()
})

test('decision lab explains why a material was excluded', async ({ page }) => {
  await page.route('**/api/v1/materials', route => route.fulfill({ json: [] }))
  await page.route('**/api/v1/intent/parse', route => route.fulfill({ json: {
    raw_text: '汽车手机支架 80℃', purpose: '汽车手机支架', max_use_temperature_c: 80,
    source: 'deterministic', confidence: .55, risk_level: 'normal', requires_manual_form: true,
    parser_message: '安全回退',
  }}))
  await page.route('**/api/v1/recommendations', route => route.fulfill({ json: {
    request_id: 'req_e2e123456', state: 'CONDITIONAL', message: '候选已通过硬约束过滤。',
    recommendations: [{
      material_key: 'POLYMAKER_HT_PLA', material_name: 'Polymaker HT-PLA', family: 'PLA composite',
      fit_score: 82, evidence_confidence: 100, evidence_status: 'approved',
      reasons: ['设备满足最低打印条件。'], tradeoffs: [], conditions: ['热性能参考值不等于安全工作温度。'],
      print_settings: { nozzle_c: { min_c: 210, max_c: 230 }, bed_c: { min_c: 25, max_c: 60 } },
      postprocessing: [], evidence_refs: [], score_breakdown: {},
    }],
    excluded: [{ material_key: 'POLYMAKER_PETG', material_name: 'Polymaker PETG', rule_id: 'R04_TEMPERATURE_MINIMUM', reason: '热性能参考值不足。' }],
    triggered_rules: ['R04_TEMPERATURE_MINIMUM'], human_escalation: false,
    ruleset_version: '1.1.0', dataset_version: 'test',
  }}))
  await page.route('**/api/v1/decision-lab/POLYMAKER_PETG', route => route.fulfill({ json: {
    material_key: 'POLYMAKER_PETG', material_name: 'Polymaker PETG', status: 'change_conditions',
    message: '以下是让该材料进入候选所需的最小条件变化。', blocking_rules: [],
    required_changes: [{ field: 'max_use_temperature_c', label: '验证更低的实际环境温度', current_value: 80, required_value: 70, rationale: '实际温度必须不超过参考值。', user_controllable: false }],
    feasible_after_changes: true, projected_fit_score: 76, projected_evidence_confidence: 100,
    evidence_refs: [], ruleset_version: '1.1.0', dataset_version: 'test',
  }}))
  await page.goto('/')
  await page.getByPlaceholder('例如：我想打印一个放在汽车里的手机支架……').fill('汽车手机支架 80℃')
  await page.getByRole('button', { name: '分析需求 →' }).click()
  await page.getByRole('button', { name: '生成可解释推荐' }).click()
  await expect(page.getByText('为什么不是这个材料？')).toBeVisible()
  await page.getByRole('button', { name: '生成决策轨迹' }).click()
  await expect(page.getByText('验证更低的实际环境温度')).toBeVisible()
  await expect(page.getByText('80℃')).toBeVisible()
  await expect(page.getByText('70℃')).toBeVisible()
})

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

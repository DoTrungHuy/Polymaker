import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import App from './App'

vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
  const url = String(input)
  if (url.endsWith('/api/v1/materials')) {
    return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  return new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } })
}))

test('renders the decision-first product promise', async () => {
  render(<App />)
  expect(screen.getByRole('heading', { name: /把“想打印什么”.*可验证的选择/ })).toBeInTheDocument()
  expect(screen.getByText('证据账本')).toBeInTheDocument()
})

// Browser -> API -> local inference -> rendered result. No mocked responses.
// Inject at the transport boundary so browser snapshots cannot capture the key.
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
const require = createRequire(new URL('../frontend/package.json', import.meta.url))
const { chromium } = require('@playwright/test')
const environment = readFileSync(new URL('../.env', import.meta.url), 'utf8')
const key = environment.match(/^ANALYSIS_API_KEY=(.*)$/m)?.[1]?.trim().replace(/^['"]|['"]$/g, '')
if (!key || !process.argv[2]) throw new Error('Configure .env and pass a local MOV path')
const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage()
  await page.route('**/api/v1/**', route => route.continue({
    headers: { ...route.request().headers(), 'x-api-key': key },
  }))
  let result
  page.on('response', async response => {
    if (response.url().includes('/api/v1/jobs/') && response.status() === 200) {
      const body = await response.json()
      if (body.status !== 'processing') result = body
    }
  })
  const start = Date.now()
  await page.goto('http://127.0.0.1:8000')
  await page.getByLabel('API-ключ', { exact: true }).fill('transport-injects-local-credential')
  await page.locator('input[type=file]').setInputFiles(process.argv[2])
  await page.getByRole('button', { name: 'Запустить анализ' }).click()
  await page.getByRole('region', { name: 'Результат анализа' }).waitFor({ timeout: 300_000 })
  assert.equal(result?.status, 'done')
  const images = page.locator('.analysis-evidence img')
  const expected = result.violations.reduce((sum, event) => sum + event.evidence_frames.length, 0)
  assert.equal(await images.count(), expected)
  if (expected) {
    await images.first().waitFor()
    await page.waitForFunction(() => Array.from(document.querySelectorAll('.analysis-evidence img'))
      .every(node => node.complete && node.naturalWidth > 0))
    assert.equal(await page.locator('.analysis-page a[href^="https://adilet.zan.kz/"]').count(),
      result.violations.length)
  }
  assert(Date.now() - start < 300_000)
  console.log(`Real UI pipeline passed: ${result.verdict}, ${result.violations.length} events, ` +
    `${expected} decoded JPEGs, ${((Date.now() - start) / 1000).toFixed(1)} seconds.`)
} catch (error) {
  console.error(String(error.message).replaceAll(key, '[REDACTED]'))
  process.exitCode = 1
} finally {
  await browser.close()
}

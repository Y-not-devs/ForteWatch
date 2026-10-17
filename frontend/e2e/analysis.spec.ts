import { expect, test } from '@playwright/test'

const accepted = { job_id: 'a'.repeat(32), status: 'processing', progress: 0, stage: 'accepted' }

async function upload(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByLabel('API-ключ', { exact: true }).fill('test-key-not-a-real-credential')
  await page.locator('input[type=file]').setInputFiles({
    name: 'sample.mov', mimeType: 'video/quicktime', buffer: Buffer.from('test'),
  })
  await page.getByRole('button', { name: 'Запустить анализ' }).click()
}

test('renders upload, real progress, no-violation verdict and limitations', async ({ page }) => {
  let polls = 0
  await page.route('**/api/v1/analyze', async route => {
    expect(route.request().headers()['x-api-key']).toBe('test-key-not-a-real-credential')
    await route.fulfill({ status: 202, json: accepted })
  })
  await page.route('**/api/v1/jobs/*', route => route.fulfill({ json: ++polls === 1
    ? { ...accepted, progress: 35, stage: 'local_inference' }
    : { ...accepted, status: 'done', progress: 100, verdict: 'no_violation',
        violations: [], elapsed_sec: 4.5, limitations: 'Предварительная проверка человеком обязательна.' },
  }))
  await upload(page)
  await expect(page.getByRole('progressbar')).toHaveAttribute('value', '35')
  await expect(page.getByRole('heading', { name: 'Нарушение не обнаружено' })).toBeVisible()
  await expect(page.getByText('Обработано за 4.5 с')).toBeVisible()
  expect(await page.evaluate(() => Object.keys(localStorage))).not.toContain('analysis_api_key')
})

test('shows a terminal failure and allows another upload', async ({ page }) => {
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 202, json: accepted }))
  await page.route('**/api/v1/jobs/*', route => route.fulfill({ json: {
    ...accepted, status: 'failed', error: 'Local model server unavailable',
  } }))
  await upload(page)
  await expect(page.getByRole('alert')).toContainText('Local model server unavailable')
  await expect(page.getByRole('button', { name: 'Запустить анализ' })).toBeEnabled()
})

test('shows events, timecodes, evidence and the verified rule source', async ({ page }) => {
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 202, json: accepted }))
  await page.route('**/api/v1/jobs/*', route => route.fulfill({ json: {
    ...accepted, status: 'done', progress: 100, verdict: 'violation', elapsed_sec: 6.5,
    limitations: 'Human review required.', violations: [{ type: 'Личные вещи', timecode_sec: 12.2,
      description: 'Видимый предмет требует проверки.', evidence_frames: [{
        timestamp_sec: 12.2,
        // A tiny test image; real JPEG decoding is covered by the 42-video HTTP evaluator.
        image_base64: '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AJgA/9k=',
      }], rule: { title: 'Личные вещи', document: 'Постановление НБРК № 231',
        section: 'Пункт 12', url: 'https://adilet.zan.kz/rus/docs/V1900019680',
        rationale: 'Проверить наличие личного предмета в кассовой зоне.' },
    }],
  } }))
  await upload(page)
  await expect(page.getByRole('heading', { name: 'Обнаружены признаки возможных нарушений' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Личные вещи — 00:12.20' })).toBeVisible()
  await expect(page.locator('.analysis-evidence img')).toHaveCount(1)
  await expect(page.locator('.analysis-evidence img')).toHaveJSProperty('naturalWidth', 1)
  await expect(page.getByRole('link', { name: /Постановление НБРК/ })).toHaveAttribute('href',
    'https://adilet.zan.kz/rus/docs/V1900019680')
})

test('shows invalid-key errors without starting a poll loop', async ({ page }) => {
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 401,
    json: { detail: 'Invalid or missing X-API-Key' },
  }))
  await upload(page)
  await expect(page.getByRole('alert')).toContainText('Invalid or missing X-API-Key')
  await expect(page.getByRole('progressbar')).toHaveCount(0)
})

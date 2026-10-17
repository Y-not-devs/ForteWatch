import { expect, test } from '@playwright/test'

const accepted = { job_id: 'a'.repeat(32), status: 'processing', progress: 0, stage: 'accepted' }

async function upload(page: import('@playwright/test').Page, buffer = Buffer.from('test')) {
  await page.goto('/')
  await page.getByLabel('API-ключ', { exact: true }).fill('test-key-not-a-real-credential')
  await page.locator('input[type=file]').setInputFiles({
    name: 'sample.mov', mimeType: 'video/quicktime', buffer,
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
  await expect(page.getByText('Браузер не поддерживает кодек этой записи.', { exact: false })).toBeVisible()
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
  await page.goto('/')
  // A locally generated playable clip tests real seeking, without dataset fixtures.
  const bytes = await page.evaluate(async () => {
    const canvas = document.createElement('canvas')
    canvas.width = 64; canvas.height = 64
    const stream = canvas.captureStream(10)
    const recorder = new MediaRecorder(stream, { mimeType: 'video/webm' })
    const chunks: BlobPart[] = []
    recorder.ondataavailable = e => chunks.push(e.data)
    const stopped = new Promise<void>(resolve => { recorder.onstop = () => resolve() })
    const timer = setInterval(() => {
      canvas.getContext('2d')!.fillRect(0, 0, 64, 64)
    }, 100)
    recorder.start()
    await new Promise(resolve => setTimeout(resolve, 2000))
    recorder.stop(); clearInterval(timer)
    await stopped
    stream.getTracks().forEach(track => track.stop())
    return Array.from(new Uint8Array(await new Blob(chunks).arrayBuffer()))
  })
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 202, json: accepted }))
  await page.route('**/api/v1/jobs/*', route => route.fulfill({ json: {
    ...accepted, status: 'done', progress: 100, verdict: 'violation', elapsed_sec: 6.5,
    limitations: 'Human review required.', violations: [{ type: 'Личные вещи', timecode_sec: 1.2,
      description: 'Видимый предмет требует проверки.', evidence_frames: [{
        timestamp_sec: 1.2,
        // A tiny test image; real JPEG decoding is covered by the 42-video HTTP evaluator.
        image_base64: '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AJgA/9k=',
      }], rule: { title: 'Личные вещи', document: 'Постановление НБРК № 231',
        section: 'Пункт 12', url: 'https://adilet.zan.kz/rus/docs/V1900019680',
        rationale: 'Проверить наличие личного предмета в кассовой зоне.' },
    }],
  } }))
  await upload(page, Buffer.from(bytes))
  await expect(page.getByRole('heading', { name: 'Обнаружены признаки возможных нарушений' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Личные вещи — 00:01.20' })).toBeVisible()
  const seek = page.getByRole('button', { name: 'Перейти к 00:01.20' })
  await expect(seek).toBeEnabled()
  await seek.click()
  await expect.poll(() => page.locator('video').evaluate(el =>
    (el as HTMLVideoElement).currentTime)).toBeCloseTo(1.2, 1)
  await expect(page.locator('video')).toHaveJSProperty('seeking', false)
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

test('restores a job after reload with a fresh key, evidence and no stored credentials', async ({ page }) => {
  const key = 'test-key-not-a-real-credential'
  let restored = false
  let finish = false
  let polls = 0
  const urls: string[] = []
  page.on('request', request => urls.push(request.url()))
  const expectNoStoredKey = async () => {
    const storage = await page.evaluate(() => ({
      local: { ...localStorage }, session: { ...sessionStorage }, url: location.href,
    }))
    expect(JSON.stringify(storage)).not.toContain(key)
    expect(JSON.stringify(storage)).not.toContain('wrong-key')
    expect(storage.session).toEqual({ 'fortewatch.last-analysis-job': accepted.job_id })
    expect(urls.some(url => url.includes(key) || url.includes(encodeURIComponent(key)))).toBe(false)
  }
  await page.route('**/api/v1/analyze', route => route.fulfill({ status: 202, json: accepted }))
  await page.route('**/api/v1/jobs/*', async route => {
    polls++
    expect(route.request().url()).toMatch(new RegExp('/jobs/' + accepted.job_id + '$'))
    if (route.request().headers()['x-api-key'] !== key) {
      await route.fulfill({ status: 401, json: { detail: 'Invalid or missing X-API-Key' } })
      return
    }
    await route.fulfill({ json: finish ? {
      ...accepted, status: 'done', progress: 100, verdict: 'violation', elapsed_sec: 4.5,
      limitations: 'Human review required.', violations: [{
        type: 'Личные вещи', timecode_sec: 1.2, description: 'Проверить предмет.',
        evidence_frames: [{ timestamp_sec: 1.2, image_base64:
          'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aPioAAAAASUVORK5CYII=' }],
        rule: { title: 'Личные вещи', document: 'Источник', section: 'Пункт 12',
          url: 'https://example.com/rule', rationale: 'Проверить событие.' },
      }],
    } : { ...accepted, progress: restored ? 35 : 0, stage: 'local_inference' } })
  })
  await upload(page)
  await expect(page.getByRole('progressbar')).toBeVisible()
  await expectNoStoredKey()
  await page.reload()
  const input = page.getByLabel('API-ключ', { exact: true })
  const restore = page.getByRole('button', { name: 'Восстановить задание' })
  await expect(input).toHaveValue('')
  await expect(restore).toBeDisabled()
  await expect(page.locator('input[type=file]')).toHaveValue('')
  await expectNoStoredKey()
  await input.fill('wrong-key')
  await restore.click()
  await expect(page.getByRole('alert')).toContainText('Неверный API-ключ')
  await expect(input).toHaveValue('')
  const failedPolls = polls
  await page.waitForTimeout(1700)
  expect(polls).toBe(failedPolls)
  await expectNoStoredKey()
  restored = true
  await input.fill(key)
  await restore.click()
  await expect(page.getByRole('progressbar')).toHaveAttribute('value', '35')
  finish = true
  await expect(page.getByRole('heading', { name: 'Обнаружены признаки возможных нарушений' })).toBeVisible()
  await expect(page.getByText('Исходное видео нужно выбрать заново', { exact: false })).toBeVisible()
  await expect(page.locator('video')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Перейти к 00:01.20' })).toBeDisabled()
  await expect(page.locator('.analysis-evidence img')).toHaveJSProperty('naturalWidth', 1)
  await expectNoStoredKey()
  // Attaching a local file to review must not submit another analysis.
  let submissions = 0
  await page.route('**/api/v1/analyze', route => { submissions++; return route.abort() })
  await page.getByLabel('Исходное видео для перемотки').setInputFiles({
    name: 'sample.mov', mimeType: 'video/quicktime', buffer: Buffer.from('test'),
  })
  await expect(page.locator('video')).toHaveCount(1)
  expect(submissions).toBe(0)
  await page.getByRole('button', { name: 'Забыть задание' }).click()
  expect(await page.evaluate(() => sessionStorage.getItem('fortewatch.last-analysis-job'))).toBeNull()
  await page.reload()
  await expect(restore).toHaveCount(0)
  await expect(input).toHaveValue('')
})

test('discards an expired job and allows a new analysis', async ({ page }) => {
  await uploadSavedJob(page)
  await page.route('**/api/v1/jobs/*', route => route.fulfill({
    status: 404, json: { detail: 'Job not found' },
  }))
  await page.getByLabel('API-ключ', { exact: true }).fill('test-key-not-a-real-credential')
  await page.getByRole('button', { name: 'Восстановить задание' }).click()
  await expect(page.getByRole('alert')).toContainText('Задание больше недоступно')
  expect(await page.evaluate(() => sessionStorage.getItem('fortewatch.last-analysis-job'))).toBeNull()
  await expect(page.getByRole('button', { name: 'Восстановить задание' })).toHaveCount(0)
  await page.locator('input[type=file]').setInputFiles({
    name: 'sample.mov', mimeType: 'video/quicktime', buffer: Buffer.from('test'),
  })
  await expect(page.getByRole('button', { name: 'Запустить анализ' })).toBeEnabled()
})

test('can forget a saved job without a key', async ({ page }) => {
  await uploadSavedJob(page)
  await page.getByRole('button', { name: 'Забыть задание' }).click()
  await page.reload()
  await expect(page.getByRole('button', { name: 'Восстановить задание' })).toHaveCount(0)
  expect(await page.evaluate(() => sessionStorage.getItem('fortewatch.last-analysis-job'))).toBeNull()
})

test('keeps the previous job when a new upload fails', async ({ page }) => {
  await uploadSavedJob(page)
  await page.route('**/api/v1/analyze', route => route.fulfill({
    status: 503, json: { detail: 'Service unavailable' },
  }))
  await upload(page)
  await expect(page.getByRole('alert')).toContainText('Service unavailable')
  expect(await page.evaluate(() => sessionStorage.getItem('fortewatch.last-analysis-job'))).toBe(accepted.job_id)
  await expect(page.getByRole('button', { name: 'Восстановить задание' })).toBeEnabled()
  await page.route('**/api/v1/jobs/*', route => route.fulfill({ json: {
    ...accepted, status: 'done', verdict: 'no_violation', elapsed_sec: 4.5,
    violations: [], limitations: 'Human review required.',
  } }))
  await page.getByRole('button', { name: 'Восстановить задание' }).click()
  await expect(page.getByRole('heading', { name: 'Нарушение не обнаружено' })).toBeVisible()
  await expect(page.locator('video')).toHaveCount(0)
  await expect(page.getByLabel('Исходное видео для перемотки')).toBeVisible()
})

async function uploadSavedJob(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.evaluate(id => sessionStorage.setItem('fortewatch.last-analysis-job', id), accepted.job_id)
  await page.reload()
}

import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  workers: 1,
  reporter: 'list',
  use: { baseURL: process.env.TEST_BASE_URL || 'http://127.0.0.1:8000', trace: 'off' },
})

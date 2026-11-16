import { defineConfig } from '@playwright/test'

// Runs against the local dev site. Not part of CI (see docs/progress/phase-0.md).
export default defineConfig({
  testDir: '.',
  // One worker: tests share users and a single dev server (parallel logins of the
  // same user caused database lock errors in CI).
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://inceptiondesign.localhost:8000',
    locale: 'ar-EG',
  },
})

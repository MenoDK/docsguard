import { defineConfig } from '@playwright/test';

// Point E2E_BASE_URL at the running lab. It must be a secure origin (localhost or https).
const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:8200';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // the lab keeps one sample project, so tests run one at a time
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
  },
});

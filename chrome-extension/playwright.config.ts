import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'url'
import path from 'path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const extensionPath = path.resolve(__dirname, 'dist')

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3456',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
      },
    },
  ],
  webServer: [
    {
      command: 'node tests/e2e/mock-ota-server.cjs',
      port: 3456,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'node tests/e2e/mock-popup-backend.cjs',
      port: 8000,
      reuseExistingServer: !process.env.CI,
    },
  ],
})

import { defineConfig } from '@playwright/test'

// Screenshot checks of the assessment pages against the preview harness (preview.html) with a fake API. Run: npx playwright test
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  outputDir: './e2e/.results',
  use: { baseURL: 'http://localhost:5199', screenshot: 'off', viewport: { width: 1440, height: 900 } },
  webServer: { command: 'npx vite --port 5199 --strictPort', url: 'http://localhost:5199/preview.html', reuseExistingServer: true, timeout: 60_000 },
  reporter: 'list',
})

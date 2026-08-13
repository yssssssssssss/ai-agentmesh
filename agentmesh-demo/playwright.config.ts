import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5181',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: '.venv/bin/python -m uvicorn agentmesh.app:app --host 127.0.0.1 --port 8021',
      cwd: '..',
      url: 'http://127.0.0.1:8021/api/auth/oauth/status',
      reuseExistingServer: false,
      env: {
        AGENTMESH_DB_PATH: '/tmp/agentmesh-playwright.sqlite3',
        AGENTMESH_DEMO_MODE: '1',
        AGENTMESH_EMBEDDING_ENABLED: 'false',
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5181',
      url: 'http://127.0.0.1:5181',
      reuseExistingServer: false,
      env: { AGENTMESH_API_PROXY: 'http://127.0.0.1:8021' },
    },
  ],
})

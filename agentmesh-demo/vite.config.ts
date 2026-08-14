import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5178,
    host: true,
    proxy: { '/api': process.env.AGENTMESH_API_PROXY ?? 'http://127.0.0.1:8010' },
  },
  test: {
    environment: 'node',
    restoreMocks: true,
  },
})

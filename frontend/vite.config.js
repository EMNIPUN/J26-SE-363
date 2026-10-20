import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load environment variables from both frontend and root project directory
  const rootEnv = loadEnv(mode, path.resolve(import.meta.dirname, '..'), '')
  const localEnv = loadEnv(mode, process.cwd(), '')
  const env = { ...rootEnv, ...localEnv }

  // Core API (FastAPI). The frontend calls /api/<path>; it is forwarded as /api/v1/<path>.
  const coreApiUrl = env.VITE_API_PROXY_TARGET || 'http://localhost:8002'

  return {
    plugins: [react(), tailwindcss()],
    test: { exclude: ['e2e/**', 'node_modules/**'] }, // the browser checks in e2e/ run with Playwright, not Vitest
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      proxy: {
        // Zero-domain local development reverse proxy (no CORS issues):
        // /api/* goes to the Core API, e.g. /api/auth/me -> http://localhost:8002/api/v1/auth/me
        // Keycloak traffic does not use this proxy: it goes to VITE_KEYCLOAK_URL directly.
        '/api': {
          target: coreApiUrl,
          changeOrigin: true,
          secure: false,
          rewrite: (path) => path.replace(/^\/api/, '/api/v1'),
        },
      },
    },
  }
})

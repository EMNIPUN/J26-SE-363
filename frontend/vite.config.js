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

  const gatewayUrl =
    env.VITE_GATEWAY_URL ||
    env.GATEWAY_PUBLIC_URL ||
    env.VITE_BACKEND_TARGET ||
    env.VITE_API_PROXY_TARGET ||
    'http://127.0.0.1:8002'

  // When /api is pointed straight at the local Core API (bypassing Kong), its
  // routes live under /api/v1, so rewrite the prefix. For a real gateway (which
  // already expects /api) no rewrite is applied.
  const targetsLocalCoreApi = /(localhost|127\.0\.0\.1):8002(\/|$)/.test(gatewayUrl)

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
        // /api/* goes to the Core API, e.g. /api/auth/me -> http://127.0.0.1:8002/api/v1/auth/me
        // Keycloak traffic does not use this proxy: it goes to VITE_KEYCLOAK_URL directly.
        '/api': {
          target: gatewayUrl,
          changeOrigin: true,
          secure: false,
          ...(targetsLocalCoreApi
            ? { rewrite: (p) => p.replace(/^\/api/, '/api/v1') }
            : {}),
        },
      },
    },
  }
})

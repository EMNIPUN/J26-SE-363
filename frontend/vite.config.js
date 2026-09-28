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
    'http://localhost:8000'

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      proxy: {
        // Zero-domain local development reverse proxy:
        // Maps /api/* calls directly to the gateway (localhost or VPS) without CORS issues
        '/api': {
          target: gatewayUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})

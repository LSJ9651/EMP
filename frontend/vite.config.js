import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendPort = env.BACKEND_PORT || '8000'
  const backendHost = env.BACKEND_HOST || 'localhost'

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: `http://${backendHost}:${backendPort}`,
          changeOrigin: true,
          timeout: 360000,
        },
      },
    },
  }
})

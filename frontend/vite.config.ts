import vue from '@vitejs/plugin-vue'
import { defineConfig, loadEnv } from 'vite'

// La clave se lee de backend/.env en el servidor de Vite y se inyecta en el proxy;
// nunca llega al navegador ni al bundle.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '../backend', '')
  return {
    plugins: [vue()],
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/api/, ''),
          headers: { 'X-API-Key': env.BOT_API_KEY ?? '' },
        },
      },
    },
  }
})

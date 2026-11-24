import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The dev server proxies the Django API so the browser sees a single origin
// (session cookie + CSRF cookie work without cross-site settings).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false },
    },
  },
})

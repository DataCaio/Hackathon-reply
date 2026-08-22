import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  base: '/dashboard/',
  plugins: [react()],
  server: {
    proxy: {
      '/final-product': 'http://127.0.0.1:8765',
    },
  },
})

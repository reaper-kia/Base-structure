import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/stt': 'http://localhost:8200',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
})
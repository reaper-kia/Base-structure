import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
      // Распознавание речи — отдельный сервис, а не бэкенд документов.
      // Без этой строки голосовой ввод в dev-режиме уходит в 404.
      '/stt': 'http://localhost:8200',
    },
  },
})

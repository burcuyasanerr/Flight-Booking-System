import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts: true // Dış tünellerden (Localtunnel, Pinggy vb.) gelen tüm bağlantılara izin ver
  }
})
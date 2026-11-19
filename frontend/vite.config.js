import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy all /api calls to Flask backend during development
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      // Proxy Socket.IO upgrade
      '/socket.io': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})

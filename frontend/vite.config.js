import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the FastAPI backend during development
    // so frontend uses relative paths like /api/* without CORS issues
    proxy: {
      '/health':   { target: 'http://localhost:8000', changeOrigin: true },
      '/agent1':   { target: 'http://localhost:8000', changeOrigin: true },
      '/agent2':   { target: 'http://localhost:8000', changeOrigin: true },
      '/agent3':   { target: 'http://localhost:8000', changeOrigin: true },
      '/agent4':   { target: 'http://localhost:8000', changeOrigin: true },
      '/agent5':   { target: 'http://localhost:8000', changeOrigin: true },
      '/scraper':  { target: 'http://localhost:8000', changeOrigin: true },
      '/demo':     { target: 'http://localhost:8000', changeOrigin: true },
      '/evaluation': { target: 'http://localhost:8000', changeOrigin: true },
      '/queue':    { target: 'http://localhost:8000', changeOrigin: true },
      '/business': { target: 'http://localhost:8000', changeOrigin: true },
      '/retry':    { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

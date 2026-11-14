import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // MARPS server (backend/run.sh): LLM, planner and map data under /api
      ...Object.fromEntries(
        ['/api', '/viewer', '/reconstructions', '/assets/ctx', '/data', '/terrain3d'].map((path) => [
          path,
          { target: process.env.MARPS_API ?? 'http://127.0.0.1:8765', changeOrigin: true },
        ]),
      ),
    },
  },
})

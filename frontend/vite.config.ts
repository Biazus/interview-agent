import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // Tailwind must run before React/Babel so @import "tailwindcss" is compiled in dev.
    tailwindcss(),
    react(),
    babel({ presets: [reactCompilerPreset()] }),
  ],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/domains': 'http://localhost:8000',
      '/topics': 'http://localhost:8000',
      '/interviews': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})

import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { mapSource } from './plugins/map-source.ts'

// Set by scripts/serve.mjs from `--map <folder>`, or directly; the synthetic fixture otherwise.
const mapDir = process.env.HARNESS_MAP_DIR ?? path.join(import.meta.dirname, 'fixtures/synthetic')

export default defineConfig({
  plugins: [react(), tailwindcss(), mapSource(mapDir)],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, './src') } },
  // Local only; the next free port is taken when several instances run.
  server: { host: '127.0.0.1', port: 5179 },
  preview: { host: '127.0.0.1', port: 5179 },
  // Pre-bundle everything up front so dev never re-optimizes mid-session (that loads two copies of React).
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      'motion/react',
      'cmdk',
      'radix-ui',
      'lucide-react',
      'shiki',
      'cn',
      'class-variance-authority',
    ],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}', 'plugins/**/*.test.ts', 'fixtures/*.test.ts'],
  },
})

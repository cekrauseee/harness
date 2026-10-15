import js from '@eslint/js'
import { defineConfig, globalIgnores } from 'eslint/config'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

// Layering: app → features → data / shared. Features never reach into the app or into each other.
const boundaries = (patterns) => ['error', { patterns }]
const internals = { group: ['@/features/*/*'], message: 'Import a feature through its index.' }
const app = { group: ['@/app', '@/app/*'], message: 'Only the app composes features.' }
const features = { group: ['@/features', '@/features/*'], message: 'Cross-feature state lives in app/ or data/.' }

export default defineConfig([
  globalIgnores(['dist', 'src/shared/ui']),
  {
    files: ['**/*.{js,mjs,ts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactHooks.configs.flat.recommended, reactRefresh.configs.vite],
    languageOptions: { globals: globals.browser },
    rules: { 'no-restricted-imports': boundaries([internals]) },
  },
  { files: ['src/features/**'], rules: { 'no-restricted-imports': boundaries([internals, app, features]) } },
  { files: ['src/data/**', 'src/shared/**'], rules: { 'no-restricted-imports': boundaries([app, features]) } },
  { files: ['*.{js,ts}', 'plugins/**', 'scripts/**', 'fixtures/**'], languageOptions: { globals: globals.node } },
])

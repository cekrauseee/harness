// Runs the Vite CLI with `--map <folder>` (or `--map=<folder>`) turned into HARNESS_MAP_DIR,
// because Vite rejects unknown flags. Every other argument goes to Vite unchanged.
import { createRequire } from 'node:module'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const args = process.argv.slice(2)
const at = args.findIndex((a) => a === '--map' || a.startsWith('--map='))
if (at >= 0) {
  const inline = args[at].startsWith('--map=')
  const dir = inline ? args[at].slice('--map='.length) : args[at + 1]
  if (!dir) {
    console.error('Usage: --map <folder>')
    process.exit(2)
  }
  process.env.HARNESS_MAP_DIR = path.resolve(dir)
  args.splice(at, inline ? 1 : 2)
}
process.argv = [process.argv[0], process.argv[1], ...args]

const vite = path.join(path.dirname(createRequire(import.meta.url).resolve('vite/package.json')), 'bin/vite.js')
await import(pathToFileURL(vite).href)

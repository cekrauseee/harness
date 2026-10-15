import fs from 'node:fs'
import path from 'node:path'
import type { Connect, Plugin } from 'vite'

// The app reads the map from this route and reloads it on this event (see src/data/source.ts).
const ROUTE = '/map/'
const CHANGED = 'harness-map:changed'
const TYPES: Record<string, string> = {
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
}

const inside = (root: string, file: string) => file === root || file.startsWith(root + path.sep)

/** Serves the regular files of one folder under /map/, read-only: GET and HEAD only, no listing,
 * no dotfiles, nothing outside the folder (symlinks included). */
export function mapMiddleware(dir: string): Connect.NextHandleFunction {
  const root = path.resolve(dir)
  return (req, res, next) => {
    const url = req.url ?? ''
    if (!url.startsWith(ROUTE)) return next()
    const fail = (status: number) => {
      res.statusCode = status
      res.end()
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.setHeader('Allow', 'GET, HEAD')
      return fail(405)
    }
    let pathname: string
    try {
      pathname = decodeURIComponent(new URL(url, 'http://localhost').pathname)
    } catch {
      return fail(400)
    }
    const rel = pathname.slice(ROUTE.length)
    if (!pathname.startsWith(ROUTE) || !rel || rel.split(/[\\/]/).some((part) => part.startsWith('.'))) return fail(404)
    let file: string
    try {
      file = fs.realpathSync(path.resolve(root, rel))
      if (!inside(fs.realpathSync(root), file) || !fs.statSync(file).isFile()) return fail(404)
    } catch {
      return fail(404)
    }
    res.setHeader('Content-Type', TYPES[path.extname(file)] ?? 'application/octet-stream')
    res.setHeader('Cache-Control', 'no-store')
    res.setHeader('X-Content-Type-Options', 'nosniff')
    if (req.method === 'HEAD') return res.end()
    fs.createReadStream(file)
      .on('error', () => fail(500))
      .pipe(res)
  }
}

/** Serves one map folder read-only and, in dev, tells the app whenever a file in it changes. */
export function mapSource(dir: string): Plugin {
  const root = path.resolve(dir)
  return {
    name: 'harness-map-source',
    configureServer(server) {
      if (!fs.existsSync(root)) server.config.logger.warn(`Map folder does not exist yet: ${root}`)
      server.middlewares.use(mapMiddleware(root))
      server.watcher.add(root)
      const notify = (file: string) => {
        if (inside(root, path.resolve(file))) server.ws.send({ type: 'custom', event: CHANGED, data: { file: path.relative(root, file) } })
      }
      server.watcher.on('add', notify).on('change', notify).on('unlink', notify)
      server.httpServer?.once('listening', () => server.config.logger.info(`  Map folder: ${root}`))
    },
    configurePreviewServer(server) {
      server.middlewares.use(mapMiddleware(root))
    },
  }
}

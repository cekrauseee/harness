// @vitest-environment node
import fs from 'node:fs'
import http from 'node:http'
import type { AddressInfo } from 'node:net'
import os from 'node:os'
import path from 'node:path'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { mapMiddleware } from './map-source'

describe('map folder middleware', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'map-source-'))
  const dir = path.join(tmp, 'map')
  let server: http.Server
  let base = ''

  beforeAll(async () => {
    fs.mkdirSync(dir)
    fs.writeFileSync(path.join(dir, 'map.json'), '{"format":"harness-map-v1"}')
    fs.writeFileSync(path.join(dir, '.secret'), 'hidden')
    fs.writeFileSync(path.join(dir, 'emap.json'), '{}')
    fs.writeFileSync(path.join(tmp, 'outside.json'), '{}')
    fs.symlinkSync(path.join(tmp, 'outside.json'), path.join(dir, 'link.json'))
    const handle = mapMiddleware(dir)
    server = http.createServer((req, res) =>
      handle(req, res, () => {
        res.statusCode = 418
        res.end()
      }),
    )
    await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
    base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`
  })

  // Raw request: fetch would normalise dot segments before they reach the server.
  const status = (urlPath: string, method = 'GET') =>
    new Promise<number>((resolve, reject) =>
      http
        .request(base + '/', { path: urlPath, method }, (res) => {
          res.resume()
          resolve(res.statusCode ?? 0)
        })
        .on('error', reject)
        .end(),
    )

  afterAll(() => {
    server.close()
    fs.rmSync(tmp, { recursive: true, force: true })
  })

  it('serves files of the folder as uncached JSON', async () => {
    const res = await fetch(`${base}/map/map.json`)
    expect(res.status).toBe(200)
    expect(res.headers.get('content-type')).toContain('application/json')
    expect(res.headers.get('cache-control')).toBe('no-store')
    expect(await res.json()).toEqual({ format: 'harness-map-v1' })
  })

  it('never reaches outside the folder or exposes hidden files', async () => {
    for (const p of [
      '/map/../outside.json',
      '/map/../abcdemap.json',
      '/map/..%2Foutside.json',
      '/map/%2E%2E/outside.json',
      '/map/link.json',
      '/map/.secret',
      '/map/',
      '/map/missing.json',
    ]) {
      expect(await status(p), p).toBe(404)
    }
  })

  it('is read-only', async () => {
    expect(await status('/map/map.json', 'PUT')).toBe(405)
    expect(await status('/map/map.json', 'DELETE')).toBe(405)
    expect(fs.readFileSync(path.join(dir, 'map.json'), 'utf8')).toBe('{"format":"harness-map-v1"}')
  })

  it('leaves other routes to the app', async () => {
    expect(await status('/src/main.tsx')).toBe(418)
  })
})

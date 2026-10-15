// @vitest-environment node
import fs from 'node:fs'
import path from 'node:path'
import { Ajv2020 } from 'ajv/dist/2020.js'
import { describe, expect, it } from 'vitest'

// The fixtures double as examples of the contract: they must validate against the canonical schema
// (repository root, or HARNESS_MAP_SCHEMA while it lives elsewhere).
const schemaPath = path.resolve(process.env.HARNESS_MAP_SCHEMA ?? path.join(import.meta.dirname, '../../../schema/map.v1.json'))
const fixtures = fs
  .readdirSync(import.meta.dirname, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => path.join(import.meta.dirname, d.name, 'map.json'))

describe.skipIf(!fs.existsSync(schemaPath))('fixtures', () => {
  it.each(fixtures)('%s matches schema/map.v1.json', (file) => {
    const validate = new Ajv2020({ allErrors: true }).compile(JSON.parse(fs.readFileSync(schemaPath, 'utf8')))
    validate(JSON.parse(fs.readFileSync(file, 'utf8')))
    expect(validate.errors ?? []).toEqual([])
  })
})

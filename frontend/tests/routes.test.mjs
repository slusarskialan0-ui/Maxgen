import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const appPath = path.resolve(__dirname, '../src/App.jsx')
const appCode = fs.readFileSync(appPath, 'utf8')

test('frontend has required route panels', () => {
  assert.ok(appCode.includes('path="/leads"'))
  assert.ok(appCode.includes('path="/kampanie"'))
  assert.ok(appCode.includes('path="/sprzedaz"'))
  assert.ok(appCode.includes('path="/oferty"'))
  assert.ok(appCode.includes('path="/sync"'))
})

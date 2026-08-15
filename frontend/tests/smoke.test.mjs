import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(process.cwd())
const appFile = fs.readFileSync(path.join(root, 'src', 'App.jsx'), 'utf8')
const apiFile = fs.readFileSync(path.join(root, 'src', 'api', 'api.js'), 'utf8')

test('app contains required business panels routes', () => {
  assert.ok(appFile.includes('/sprzedaz'))
  assert.ok(appFile.includes('/oferty'))
  assert.ok(appFile.includes('/ruch'))
  assert.ok(appFile.includes('/przychody'))
})

test('api client has local fallback', () => {
  assert.ok(apiFile.includes('VITE_API_URL'))
  assert.ok(apiFile.includes('http://localhost:8000'))
})

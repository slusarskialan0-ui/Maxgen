import axios from 'axios'

const sanitizeBase = (value) => String(value || '').trim().replace(/\/+$/, '')
const withPath = (base, path = '') => `${sanitizeBase(base)}${path.startsWith('/') ? path : `/${path}`}`
const isAbsoluteUrl = (value) => /^https?:\/\//i.test(String(value || ''))

// AUTO-CONNECT: chooses best reachable API endpoint without manual integration.
const API_BASE_FALLBACK = 'http://localhost:8000'
const envBase = sanitizeBase(import.meta.env.VITE_API_URL || '')
const runtimeCandidates = (() => {
  if (typeof window === 'undefined') return []
  const { origin, protocol, hostname, port } = window.location
  const portBasedBackend = port === '3000' ? `${protocol}//${hostname}:8000` : ''
  return [origin, portBasedBackend]
})()

const API_BASE_CANDIDATES = Array.from(new Set([
  envBase,
  ...runtimeCandidates.map(sanitizeBase),
  API_BASE_FALLBACK,
  'http://127.0.0.1:8000',
].filter(Boolean)))

let resolvedApiBase = envBase || API_BASE_FALLBACK
let resolvePromise = null
let lastResolveTs = 0
const RESOLVE_TTL_MS = 60000

async function probeHealth(base, timeoutMs = 2200) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(withPath(base, '/health'), {
      method: 'GET',
      cache: 'no-store',
      signal: controller.signal,
    })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

async function resolveApiBase(options = {}) {
  const force = Boolean(options.force)
  if (resolvePromise) {
    if (!force) return resolvePromise
    await resolvePromise
  }
  if (!force && resolvedApiBase && (Date.now() - lastResolveTs) < RESOLVE_TTL_MS) {
    return resolvedApiBase
  }

  const run = (async () => {
    for (const candidate of API_BASE_CANDIDATES) {
      if (await probeHealth(candidate)) {
        resolvedApiBase = candidate
        lastResolveTs = Date.now()
        return resolvedApiBase
      }
    }
    resolvedApiBase = envBase || API_BASE_FALLBACK
    lastResolveTs = Date.now()
    return resolvedApiBase
  })()
  resolvePromise = run

  try {
    return await run
  } finally {
    if (resolvePromise === run) resolvePromise = null
  }
}

function getApiBase() {
  return sanitizeBase(resolvedApiBase || envBase || API_BASE_FALLBACK)
}

function buildApiUrl(path = '') {
  return path ? withPath(getApiBase(), path) : getApiBase()
}

const initialApiBase = getApiBase()

const api = axios.create({
  baseURL: initialApiBase,
  timeout: 30000,
})

api.interceptors.request.use(async (config) => {
  if (isAbsoluteUrl(config?.url)) return config
  const base = await resolveApiBase()
  return { ...config, baseURL: base }
})

// Retry failed requests once for network/5xx errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error.config
    if (!config || config._retry) return Promise.reject(error)
    const status = error.response?.status
    const isRetryable = !status || status >= 500
    if (isRetryable) {
      config._retry = true
      const base = await resolveApiBase({ force: true })
      if (!isAbsoluteUrl(config.url)) config.baseURL = base
      await new Promise((resolve) => setTimeout(resolve, 600))
      return api(config)
    }
    return Promise.reject(error)
  }
)

export default api
export { buildApiUrl, getApiBase, resolveApiBase }

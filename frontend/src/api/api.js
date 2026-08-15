import axios from 'axios'

// AUTO-CONNECT:
// 1) explicit env override
// 2) Vercel production proxy (/api -> Fly backend)
// 3) local development fallback
const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? '/api' : 'http://localhost:8000')

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
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
      await new Promise((resolve) => setTimeout(resolve, 600))
      return api(config)
    }
    return Promise.reject(error)
  }
)

export default api
export { API_BASE }

/**
 * Setup / Configuration API helpers.
 */
import api from './api'

export const setupApi = {
  /** Save config keys to DB (live, no restart needed). */
  save: (data) => api.post('/api/setup/save', data),

  /** Send a test Telegram message. */
  testTelegram: (token, chatId) =>
    api.post('/api/setup/test-telegram', { token, chat_id: chatId }),

  /** Test PostgreSQL/SQLite connection and run migrations. */
  testDb: (databaseUrl) =>
    api.post('/api/setup/test-db', { database_url: databaseUrl }),

  /** Get current configuration status. */
  getStatus: () => api.get('/api/setup/status'),
}

export const b2bApi = {
  /** Trigger a one-off scraping scan. */
  triggerScan: () => api.post('/api/b2b/scan'),

  /** List B2B leads with optional filters. */
  getLeads: (params = {}) => api.get('/api/b2b/leads', { params }),

  /** Get scanner on/off status. */
  getScannerStatus: () => api.get('/api/b2b/scanner/status'),

  /** Toggle scanner on/off. */
  toggleScanner: () => api.post('/api/b2b/scanner/toggle'),
}

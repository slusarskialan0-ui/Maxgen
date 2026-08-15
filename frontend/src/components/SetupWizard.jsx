import React, { useMemo, useState } from 'react'
import api, { API_BASE } from '../api/api'

function Indicator({ ok }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-green-500' : 'bg-gray-300'}`} />
}

export default function SetupWizard() {
  const [telegramToken, setTelegramToken] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')
  const [databaseUrl, setDatabaseUrl] = useState(() => localStorage.getItem('setup_database_url') || '')
  const [telegramState, setTelegramState] = useState({ ok: false, msg: '' })
  const [dbState, setDbState] = useState({ ok: false, msg: '' })
  const [copyState, setCopyState] = useState('')
  const [loading, setLoading] = useState({ telegram: false, db: false })

  const healthCheckUrl = useMemo(() => `${API_BASE.replace(/\/$/, '')}/health`, [])

  const testTelegram = async () => {
    setLoading((v) => ({ ...v, telegram: true }))
    setTelegramState({ ok: false, msg: '' })
    try {
      await api.post('/api/setup/test-telegram', {
        telegram_bot_token: telegramToken,
        telegram_chat_id: telegramChatId,
      })
      setTelegramState({ ok: true, msg: 'Test wysłany. Sprawdź Telegram.' })
    } catch (error) {
      setTelegramState({ ok: false, msg: error?.response?.data?.detail || 'Błąd testu Telegram.' })
    } finally {
      setLoading((v) => ({ ...v, telegram: false }))
    }
  }

  const testDb = async () => {
    setLoading((v) => ({ ...v, db: true }))
    setDbState({ ok: false, msg: '' })
    try {
      await api.post('/api/setup/test-db', { database_url: databaseUrl })
      setDbState({ ok: true, msg: 'Połączenie OK. Baza gotowa.' })
      localStorage.setItem('setup_database_url', databaseUrl)
    } catch (error) {
      setDbState({ ok: false, msg: error?.response?.data?.detail || 'Błąd połączenia z bazą.' })
    } finally {
      setLoading((v) => ({ ...v, db: false }))
    }
  }

  const copyHealth = async () => {
    try {
      await navigator.clipboard.writeText(healthCheckUrl)
      setCopyState('Skopiowano URL health-check.')
    } catch {
      setCopyState('Nie udało się skopiować URL.')
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">🧩 Setup Wizard / Integrations Hub</h1>
        <p className="mt-1 text-sm text-gray-500">Skonfiguruj Telegram, bazę PostgreSQL i keep-alive.</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <section className="rounded-2xl border bg-white p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Telegram</h2>
            <Indicator ok={telegramState.ok} />
          </div>
          <div className="grid grid-cols-1 gap-2">
            <a href="https://t.me/BotFather" target="_blank" rel="noreferrer" className="inline-flex justify-center rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-50">
              1. Otwórz BotFather
            </a>
            <a href="https://t.me/userinfobot" target="_blank" rel="noreferrer" className="inline-flex justify-center rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-50">
              2. Pobierz Chat ID
            </a>
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">TELEGRAM_BOT_TOKEN</label>
            <input className="w-full rounded-lg border px-3 py-2 text-sm" value={telegramToken} onChange={(e) => setTelegramToken(e.target.value)} placeholder="123456:ABC..." />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">TELEGRAM_CHAT_ID</label>
            <input className="w-full rounded-lg border px-3 py-2 text-sm" value={telegramChatId} onChange={(e) => setTelegramChatId(e.target.value)} placeholder="np. 123456789" />
          </div>
          <button onClick={testTelegram} disabled={loading.telegram} className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60">
            {loading.telegram ? 'Wysyłanie...' : 'Wyślij testowy alert'}
          </button>
          {telegramState.msg && <p className={`text-xs ${telegramState.ok ? 'text-green-600' : 'text-red-600'}`}>{telegramState.msg}</p>}
        </section>

        <section className="rounded-2xl border bg-white p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Baza danych (PostgreSQL)</h2>
            <Indicator ok={dbState.ok} />
          </div>
          <a href="https://neon.tech" target="_blank" rel="noreferrer" className="inline-flex w-full justify-center rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-50">
            Załóż darmową bazę na Neon.tech
          </a>
          <div>
            <label className="mb-1 block text-xs text-gray-500">DATABASE_URL</label>
            <input className="w-full rounded-lg border px-3 py-2 text-sm" value={databaseUrl} onChange={(e) => setDatabaseUrl(e.target.value)} placeholder="postgresql://..." />
          </div>
          <button onClick={testDb} disabled={loading.db} className="w-full rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60">
            {loading.db ? 'Testowanie...' : 'Testuj i Zapisz Bazę'}
          </button>
          {dbState.msg && <p className={`text-xs ${dbState.ok ? 'text-green-600' : 'text-red-600'}`}>{dbState.msg}</p>}
        </section>

        <section className="rounded-2xl border bg-white p-6 space-y-4">
          <h2 className="text-lg font-semibold">Keep-Alive (UptimeRobot)</h2>
          <p className="text-sm text-gray-500">Dodaj endpoint health-check do monitora (np. co 5 minut).</p>
          <div className="rounded-lg bg-gray-50 border px-3 py-2 font-mono text-xs break-all">{healthCheckUrl}</div>
          <button onClick={copyHealth} className="w-full rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-900">
            Skopiuj URL Health-Check
          </button>
          {copyState && <p className="text-xs text-blue-600">{copyState}</p>}
        </section>
      </div>
    </div>
  )
}

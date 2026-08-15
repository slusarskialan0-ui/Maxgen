import React, { useEffect, useState } from 'react'
import { setupApi } from '../api/config'

const TABS = ['telegram', 'database', 'keepalive']

const TAB_LABELS = {
  telegram: '📱 Telegram',
  database: '🗄️ Baza Danych',
  keepalive: '🔁 Keep-Alive',
}

function StatusDot({ ok }) {
  return (
    <span
      className={`inline-block w-3 h-3 rounded-full ml-2 ${ok ? 'bg-green-500' : 'bg-gray-300'}`}
      title={ok ? 'Skonfigurowane' : 'Nieskonfigurowane'}
    />
  )
}

export default function SetupWizard() {
  const [tab, setTab] = useState('telegram')
  const [status, setStatus] = useState(null)

  // Telegram form
  const [tgToken, setTgToken] = useState('')
  const [tgChatId, setTgChatId] = useState('')
  const [tgMsg, setTgMsg] = useState('')
  const [tgLoading, setTgLoading] = useState(false)

  // DB form
  const [dbUrl, setDbUrl] = useState('')
  const [dbMsg, setDbMsg] = useState('')
  const [dbLoading, setDbLoading] = useState(false)

  // Threshold
  const [threshold, setThreshold] = useState('65')

  const loadStatus = async () => {
    try {
      const res = await setupApi.getStatus()
      setStatus(res.data)
      setThreshold(String(res.data.b2b_scanner?.score_threshold ?? 65))
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadStatus()
  }, [])

  const handleTestTelegram = async () => {
    if (!tgToken || !tgChatId) {
      setTgMsg('❌ Wypełnij oba pola')
      return
    }
    setTgLoading(true)
    setTgMsg('')
    try {
      await setupApi.testTelegram(tgToken, tgChatId)
      setTgMsg('✅ Połączenie działa! Wiadomość testowa wysłana.')
      await loadStatus()
    } catch (err) {
      setTgMsg(`❌ Błąd: ${err.response?.data?.detail || err.message}`)
    } finally {
      setTgLoading(false)
    }
  }

  const handleSaveTelegram = async () => {
    try {
      await setupApi.save({
        TELEGRAM_BOT_TOKEN: tgToken,
        TELEGRAM_CHAT_ID: tgChatId,
        B2B_LEAD_SCORE_THRESHOLD: threshold,
      })
      setTgMsg('✅ Zapisano konfigurację')
      await loadStatus()
    } catch (err) {
      setTgMsg(`❌ ${err.response?.data?.detail || err.message}`)
    }
  }

  const handleTestDb = async () => {
    if (!dbUrl) {
      setDbMsg('❌ Podaj DATABASE_URL')
      return
    }
    setDbLoading(true)
    setDbMsg('')
    try {
      await setupApi.testDb(dbUrl)
      setDbMsg('✅ Baza podłączona! Migracje wykonane.')
      await loadStatus()
    } catch (err) {
      setDbMsg(`❌ Błąd: ${err.response?.data?.detail || err.message}`)
    } finally {
      setDbLoading(false)
    }
  }

  const handleCopyHealth = () => {
    const apiBase = import.meta.env.VITE_API_URL || window.location.origin
    const url = `${apiBase}/health`
    navigator.clipboard.writeText(url).then(() => alert(`Skopiowano: ${url}`))
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">⚙️ Kreator Konfiguracji</h1>
      <p className="text-sm text-gray-500 mb-6">
        Połącz wszystkie usługi bez restartowania serwera.
      </p>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              tab === t
                ? 'bg-white border border-b-white border-gray-200 -mb-px text-blue-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {TAB_LABELS[t]}
            {t === 'telegram' && status && (
              <StatusDot ok={status.telegram?.configured} />
            )}
            {t === 'database' && status && (
              <StatusDot ok={status.database?.configured} />
            )}
          </button>
        ))}
      </div>

      {/* ── TELEGRAM ── */}
      {tab === 'telegram' && (
        <div className="space-y-4">
          <div className="rounded-xl border bg-blue-50 p-4 space-y-2 text-sm text-blue-800">
            <p className="font-semibold">Krok 1 — Utwórz bota i znajdź swój Chat ID</p>
            <div className="flex gap-2 flex-wrap">
              <a
                href="https://t.me/BotFather"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-blue-700"
              >
                🤖 Otwórz BotFather
              </a>
              <a
                href="https://t.me/userinfobot"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 bg-gray-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-gray-800"
              >
                🆔 Znajdź swój Chat ID
              </a>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Bot Token <span className="text-red-500">*</span>
            </label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="1234567890:AAFxxx..."
              value={tgToken}
              onChange={(e) => setTgToken(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Chat ID <span className="text-red-500">*</span>
            </label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="-1001234567890"
              value={tgChatId}
              onChange={(e) => setTgChatId(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Próg LeadScore (alerty ≥ tej wartości)
            </label>
            <input
              type="number"
              min={1}
              max={100}
              className="w-32 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>

          {tgMsg && (
            <div className={`rounded-lg px-4 py-2 text-sm ${tgMsg.startsWith('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {tgMsg}
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleTestTelegram}
              disabled={tgLoading}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
            >
              {tgLoading ? '⏳ Testuję...' : '🔌 Testuj Połączenie'}
            </button>
            <button
              onClick={handleSaveTelegram}
              className="flex-1 bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-700"
            >
              💾 Zapisz
            </button>
          </div>

          {status?.telegram?.configured && (
            <div className="flex items-center gap-2 text-sm text-green-700 font-medium">
              <span className="w-3 h-3 bg-green-500 rounded-full inline-block" />
              Telegram skonfigurowany (token: {status.telegram.token_masked})
            </div>
          )}
        </div>
      )}

      {/* ── DATABASE ── */}
      {tab === 'database' && (
        <div className="space-y-4">
          <div className="rounded-xl border bg-purple-50 p-4 text-sm text-purple-800 space-y-2">
            <p className="font-semibold">Darmowa baza PostgreSQL (Neon.tech)</p>
            <a
              href="https://neon.tech"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 bg-purple-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-purple-700"
            >
              🚀 Zarejestruj się na Neon.tech (za darmo)
            </a>
            <p className="text-xs text-purple-600 mt-1">
              Bez DATABASE_URL system automatycznie używa lokalnej bazy SQLite.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              DATABASE_URL (PostgreSQL lub SQLite)
            </label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="******host/dbname lub sqlite:///./leads.db"
              value={dbUrl}
              onChange={(e) => setDbUrl(e.target.value)}
            />
          </div>

          {dbMsg && (
            <div className={`rounded-lg px-4 py-2 text-sm ${dbMsg.startsWith('✅') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
              {dbMsg}
            </div>
          )}

          <button
            onClick={handleTestDb}
            disabled={dbLoading}
            className="w-full bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-purple-700 disabled:opacity-50"
          >
            {dbLoading ? '⏳ Łączę...' : '🔌 Połącz i Zapisz'}
          </button>

          {status?.database?.configured && (
            <div className="flex items-center gap-2 text-sm text-green-700 font-medium">
              <span className="w-3 h-3 bg-green-500 rounded-full inline-block" />
              {status.database.type === 'postgresql' ? '🐘 PostgreSQL' : '🗃️ SQLite'} podłączona
            </div>
          )}
        </div>
      )}

      {/* ── KEEP-ALIVE ── */}
      {tab === 'keepalive' && (
        <div className="space-y-4">
          <div className="rounded-xl border bg-amber-50 p-4 text-sm text-amber-800 space-y-3">
            <p className="font-semibold">🔁 Zapobiegaj uśpieniu serwera (Render Free Tier)</p>
            <p>
              Usługi na darmowym planie Render.com usypiają po 15 minutach bezczynności.
              Dodaj poniższy URL do UptimeRobot, aby pingować serwer co 5 minut.
            </p>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={handleCopyHealth}
                className="bg-amber-600 text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-amber-700"
              >
                📋 Kopiuj URL /health
              </button>
              <a
                href="https://uptimerobot.com"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center bg-gray-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold hover:bg-gray-800"
              >
                🤖 Otwórz UptimeRobot
              </a>
            </div>
            <p className="text-xs text-amber-600">
              Baza danych jest automatycznie czyszczona raz w tygodniu (cron-sweeper usuwa leady starsze niż 30 dni).
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

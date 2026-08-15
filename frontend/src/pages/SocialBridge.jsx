import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

const PARAM_FIELDS = {
  facebook_messenger: [
    { key: 'page_id', label: 'ID strony FB / username', placeholder: 'np. PolaAutoLeads' },
    { key: 'ref', label: 'Ref (opcjonalnie)', placeholder: 'np. campaign1' },
  ],
  facebook_group: [
    { key: 'group_id', label: 'ID / slug grupy FB', placeholder: 'np. polskie-auto-dealers' },
  ],
  facebook_post: [
    { key: 'url', label: 'URL do udostępnienia', placeholder: 'https://...' },
    { key: 'text', label: 'Tekst (opcjonalnie)', placeholder: 'Sprawdź tę ofertę!' },
  ],
  telegram_chat: [
    { key: 'username', label: 'Username / ID', placeholder: 'np. PolaAutoLeads_bot' },
    { key: 'message', label: 'Wiadomość (opcjonalnie)', placeholder: 'Cześć! Interesuję się...' },
  ],
  telegram_channel: [
    { key: 'channel', label: 'Nazwa kanału', placeholder: 'np. polska_auto_leads' },
  ],
  whatsapp: [
    { key: 'phone', label: 'Numer (bez +)', placeholder: 'np. 48123456789' },
    { key: 'message', label: 'Wiadomość (opcjonalnie)', placeholder: 'Dzień dobry...' },
  ],
  linkedin: [
    { key: 'company', label: 'Slug firmy LinkedIn', placeholder: 'np. polska-auto-leads' },
  ],
  otomoto: [
    { key: 'make', label: 'Marka auta', placeholder: 'np. BMW' },
    { key: 'model', label: 'Model', placeholder: 'np. 3 Series' },
  ],
  olx: [
    { key: 'query', label: 'Fraza wyszukiwania', placeholder: 'np. BMW e46' },
  ],
  allegro: [
    { key: 'query', label: 'Fraza wyszukiwania', placeholder: 'np. części BMW' },
  ],
}

export default function SocialBridge() {
  const [platforms, setPlatforms] = useState([])
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [params, setParams] = useState({})
  const [connecting, setConnecting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [error, setError] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [platRes, evRes] = await Promise.all([
        api.get('/api/social/platforms'),
        api.get('/api/social/events?limit=20'),
      ])
      setPlatforms(platRes.data)
      setEvents(evRes.data)
    } catch (e) {
      setError('Błąd ładowania danych: ' + (e?.message || ''))
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  const handleSelectPlatform = (platform) => {
    setSelected(platform)
    setParams({})
    setLastResult(null)
    setError('')
  }

  const handleConnect = async () => {
    if (!selected) return
    setConnecting(true)
    setError('')
    try {
      const res = await api.post(`/api/social/connect/${selected.platform}`, { params })
      setLastResult(res.data)
      window.open(res.data.target_url, '_blank', 'noopener,noreferrer')
      await loadData()
    } catch (e) {
      setError('Błąd: ' + (e?.response?.data?.detail || e?.message || 'Nieznany błąd'))
    }
    setConnecting(false)
  }

  const fields = selected ? (PARAM_FIELDS[selected.platform] || []) : []

  if (loading) return <div className="p-8 text-gray-400">Ładowanie platform...</div>

  return (
    <div className="p-6 space-y-6">
      {/* Nagłówek */}
      <div>
        <h1 className="text-2xl font-bold">🔗 Social Bridge</h1>
        <p className="text-sm text-gray-500 mt-1">
          Deep-linking z social mediami i zewnętrznymi platformami B2B — kliknij platformę, wypełnij dane i otwórz w jednym kliknięciu.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Lista platform */}
        <div>
          <h2 className="font-semibold text-gray-700 mb-3">Wybierz platformę</h2>
          <div className="grid grid-cols-2 gap-3">
            {platforms.map((p) => (
              <button
                key={p.platform}
                onClick={() => handleSelectPlatform(p)}
                className={`flex items-center gap-2 p-3 rounded-xl border text-left transition-all ${
                  selected?.platform === p.platform
                    ? 'border-blue-500 bg-blue-50 shadow'
                    : 'border-gray-200 bg-white hover:border-blue-300 hover:bg-blue-50'
                }`}
              >
                <span className="text-2xl">{p.icon}</span>
                <div>
                  <div className="text-sm font-medium text-gray-800">{p.label}</div>
                  <div className="text-xs text-gray-400 leading-tight">{p.description}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Panel konfiguracji */}
        <div>
          {selected ? (
            <div className="bg-white rounded-xl border p-5 space-y-4">
              <h2 className="font-semibold text-gray-700 flex items-center gap-2">
                <span className="text-2xl">{selected.icon}</span>
                {selected.label}
              </h2>
              <p className="text-sm text-gray-500">{selected.description}</p>

              {fields.map((f) => (
                <div key={f.key}>
                  <label className="text-xs text-gray-500 block mb-1">{f.label}</label>
                  <input
                    className="border rounded-lg px-3 py-2 text-sm w-full focus:outline-none focus:border-blue-400"
                    placeholder={f.placeholder}
                    value={params[f.key] || ''}
                    onChange={(e) => setParams((prev) => ({ ...prev, [f.key]: e.target.value }))}
                  />
                </div>
              ))}

              <button
                onClick={handleConnect}
                disabled={connecting}
                className="w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {connecting ? 'Łączenie...' : `🚀 Otwórz ${selected.label}`}
              </button>

              {lastResult && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm">
                  <div className="font-medium text-green-700 mb-1">✅ Link wygenerowany</div>
                  <a
                    href={lastResult.target_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 break-all text-xs hover:underline"
                  >
                    {lastResult.target_url}
                  </a>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-50 rounded-xl border border-dashed border-gray-300 p-10 flex items-center justify-center text-gray-400 text-sm">
              ← Wybierz platformę z listy
            </div>
          )}
        </div>
      </div>

      {/* Historia zdarzeń */}
      <div>
        <h2 className="font-semibold text-gray-700 mb-3">📋 Historia aktywacji (ostatnie 20)</h2>
        {events.length === 0 ? (
          <div className="text-gray-400 text-sm">Brak zdarzeń. Kliknij przycisk platformy, aby rozpocząć.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b">
                  <th className="pb-2 pr-4">Platforma</th>
                  <th className="pb-2 pr-4">URL</th>
                  <th className="pb-2 pr-4">Data</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-2 pr-4 font-medium text-gray-700">
                      {platforms.find((p) => p.platform === ev.platform)?.icon || '🔗'}{' '}
                      {ev.platform}
                    </td>
                    <td className="py-2 pr-4 max-w-xs truncate">
                      <a
                        href={ev.target_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline text-xs"
                      >
                        {ev.target_url}
                      </a>
                    </td>
                    <td className="py-2 text-xs text-gray-400 whitespace-nowrap">
                      {ev.created_at ? new Date(ev.created_at).toLocaleString('pl-PL') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import api from '../api/api'

const ROADMAP = [
  { title: 'Dynamic scoring leadów', priority: 'P1', status: 'in_progress', description: 'Priorytetyzacja leadów na podstawie revenue, źródła i historii.' },
  { title: 'Multi-tenant billing', priority: 'P1', status: 'planned', description: 'Oddzielne limity i billing dla każdego projektu agencyjnego.' },
  { title: 'Voice AI outreach', priority: 'P2', status: 'planned', description: 'Automatyczne rozmowy follow-up dla leadów premium.' },
  { title: 'Predictive churn', priority: 'P1', status: 'done', description: 'Model wczesnego ostrzegania dla odpływu klientów.' },
  { title: 'Autonomiczny self-healing', priority: 'P2', status: 'in_progress', description: 'Samonaprawa pipeline i anomalii wydajnościowych.' },
  { title: 'Marketplace syndication', priority: 'P3', status: 'planned', description: 'Dystrybucja leadów do partnerów i resellerów.' },
]

const SUGGESTIONS = [
  'Uruchom kampanie dla województw z najwyższym revenue.',
  'Wzmocnij onboarding Starter → Pro dla klientów o wysokim usage.',
  'Przetestuj ofertę white-label dla agencji regionalnych.',
  'Dodaj SLA alerty dla pipeline powyżej 80 req/min.',
  'Połącz scoring leadów z heatmapą przychodów.',
]

const DEFAULT_EVOLUTION_RUN = {
  voivodeship: 'mazowieckie',
  industries: ['mechanik', 'dealer samochodowy', 'wulkanizacja'],
  limit: 24,
  keep_latest_backups: 8,
}

export default function AutoRozwoj() {
  const [forecast, setForecast] = useState(null)
  const [report, setReport] = useState(null)
  const [running, setRunning] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [darkMode, setDarkMode] = useState(false)

  const loadReport = async () => {
    const response = await api.get('/evolution/report')
    setReport(response.data)
  }

  useEffect(() => {
    api.get('/system/forecast').then((response) => setForecast(response.data)).catch(() => {})
    loadReport().catch(() => {})
  }, [])

  useEffect(() => {
    if (!autoRefresh) return undefined
    const timer = setInterval(() => {
      loadReport().catch(() => {})
    }, 12000)
    return () => clearInterval(timer)
  }, [autoRefresh])

  const runEvolutionMode = async () => {
    setRunning(true)
    try {
      const response = await api.post('/evolution/run', DEFAULT_EVOLUTION_RUN)
      setReport(response.data.report)
      await api.get('/system/forecast').then((res) => setForecast(res.data)).catch(() => {})
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className={`p-8 space-y-6 ${darkMode ? 'bg-slate-950 text-slate-100 min-h-screen' : ''}`}>
      <div>
        <h1 className="text-2xl font-bold">🧠 AUTO-ROZWÓJ</h1>
        <p className="mt-1 text-sm text-gray-500">Roadmap, propozycje systemu i rekomendacje priorytetów.</p>
      </div>

      <div className={`rounded-2xl border p-4 flex flex-wrap items-center gap-3 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white'}`}>
        <button
          onClick={runEvolutionMode}
          disabled={running}
          className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {running ? 'OVERKILL EVOLUTION MODE…' : 'Uruchom OVERKILL EVOLUTION MODE'}
        </button>
        <button
          onClick={() => setAutoRefresh((v) => !v)}
          className="rounded-xl border px-4 py-2 text-sm font-semibold"
        >
          Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
        </button>
        <button
          onClick={() => setDarkMode((v) => !v)}
          className="rounded-xl border px-4 py-2 text-sm font-semibold"
        >
          Tryb: {darkMode ? 'Dark' : 'Light'}
        </button>
      </div>

      <div className="rounded-2xl border bg-gradient-to-r from-indigo-600 to-blue-600 p-6 text-white">
        <div className="text-sm uppercase tracking-wide opacity-80">Priority AI recommendations</div>
        <div className="mt-2 text-2xl font-bold">Najbliższe ryzyko: {forecast?.next_pipeline_issue || 'none'}</div>
        <div className="mt-2 text-blue-50">Confidence: {forecast?.confidence_pct || 95}% · rekomendacja: rozwijać AUTO-ANALYTICS + self-healing.</div>
      </div>

      <div className={`rounded-2xl border p-6 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white'}`}>
        <h2 className="mb-4 text-lg font-semibold">Raport OVERKILL EVOLUTION MODE</h2>
        {!report && <div className="text-sm text-gray-500">Brak raportu — uruchom tryb evolution.</div>}
        {report && (
          <div className="space-y-3 text-sm">
            <div>Status API: <span className="font-semibold">{report?.status_api?.status || 'unknown'}</span></div>
            <div>Status Frontendu: <span className="font-semibold">{report?.status_frontend?.status || 'unknown'}</span></div>
            <div>Status Bazy: <span className="font-semibold">{report?.status_database?.status || 'unknown'}</span></div>
            <div>Status Automatyzacji: <span className="font-semibold">{report?.status_automation?.status || 'unknown'}</span></div>
            <div>Status Leadów: <span className="font-semibold">{report?.status_leads?.status || 'unknown'}</span></div>
            <div>Status Sprzedaży: <span className="font-semibold">{report?.status_sales?.status || 'unknown'}</span></div>
            <div>Status Dashboardów: <span className="font-semibold">{report?.status_dashboards?.status || 'unknown'}</span></div>
            <div>Status AI-autonomii: <span className="font-semibold">{report?.status_ai_autonomy?.status || 'unknown'}</span></div>
            <div>Status EVOLUTION MODE: <span className="font-semibold">{report?.status_evolution_mode?.status || 'unknown'}</span></div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className={`rounded-2xl border p-6 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white'}`}>
          <h2 className="mb-4 text-lg font-semibold">Roadmap</h2>
          <div className="space-y-4">
            {ROADMAP.map((item) => (
              <div key={item.title} className={`rounded-xl border p-4 ${darkMode ? 'border-slate-700' : ''}`}>
                <div className="flex items-center justify-between gap-4">
                  <div className="font-semibold">{item.title}</div>
                  <div className="text-xs font-bold text-blue-600">{item.priority}</div>
                </div>
                <div className="mt-1 text-sm text-gray-500">{item.description}</div>
                <div className="mt-3 inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">{item.status}</div>
              </div>
            ))}
          </div>
        </div>

        <div className={`rounded-2xl border p-6 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white'}`}>
          <h2 className="mb-4 text-lg font-semibold">Feature suggestions</h2>
          <div className="space-y-3">
            {SUGGESTIONS.map((suggestion, index) => (
              <div key={suggestion} className="rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
                <span className="mr-2 font-bold text-blue-600">#{index + 1}</span>
                {suggestion}
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">
            AI priorytet: skaluj marketplace i billing tam, gdzie revenue/voivodeship jest najwyższe.
          </div>
        </div>
      </div>
    </div>
  )
}

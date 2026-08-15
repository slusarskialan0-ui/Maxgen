import React, { useCallback, useEffect, useState } from 'react'
import api from '../api/api'

const GENERATORS = [
  { key: 'traffic', label: 'Ruch', endpoint: '/generators/traffic', source: 'ruch' },
  { key: 'campaign', label: 'Kampania', endpoint: '/generators/campaign', source: 'kampania' },
  { key: 'forms', label: 'Formularze', endpoint: '/generators/forms', source: 'formularz' },
  { key: 'ads', label: 'Reklamy', endpoint: '/generators/ads', source: 'reklama' },
  { key: 'social', label: 'Social Media', endpoint: '/generators/social', source: 'social_media' },
  { key: 'marketplace', label: 'Marketplace', endpoint: '/generators/marketplace', source: 'marketplace' },
]

export default function GeneratorsPage() {
  const [leads, setLeads] = useState([])
  const [results, setResults] = useState({})
  const [loadingKey, setLoadingKey] = useState('')
  const [message, setMessage] = useState('')

  const load = useCallback(async () => {
    try {
      const r = await api.get('/leads', { params: { limit: 20 } })
      setLeads(r.data.items || [])
    } catch { }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [load])

  const runGenerator = async (generator) => {
    setLoadingKey(generator.key)
    setMessage('')
    try {
      const r = await api.get(generator.endpoint)
      setResults(prev => ({ ...prev, [generator.key]: r.data.added || 0 }))
      setMessage(`Dodano ${r.data.added || 0} leadów dla źródła ${generator.source}.`)
      load()
    } catch {
      setMessage(`Nie udało się uruchomić generatora ${generator.label}.`)
    }
    setLoadingKey('')
  }

  const runAll = async () => {
    setLoadingKey('all')
    setMessage('')
    try {
      const r = await api.post('/generators/run-all')
      const next = {}
      ;(r.data.results || []).forEach(item => { next[item.source] = item.added })
      setResults(prev => ({ ...prev, ...next }))
      setMessage(`Uruchomiono wszystkie generatory. Dodano ${r.data.added || 0} leadów.`)
      load()
    } catch {
      setMessage('Nie udało się uruchomić wszystkich generatorów.')
    }
    setLoadingKey('')
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">🧪 Generatory leadów offline</h1>
          <p className="text-sm text-gray-500 mt-1">Symulacja ruchu, kampanii i źródeł offline z automatycznym zapisem do bazy.</p>
        </div>
        <button onClick={runAll} disabled={loadingKey === 'all'} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {loadingKey === 'all' ? 'Uruchamiam...' : 'Uruchom wszystkie'}
        </button>
      </div>

      {message && <div className="rounded-xl border bg-blue-50 border-blue-200 text-blue-800 text-sm p-4">{message}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {GENERATORS.map(generator => (
          <div key={generator.key} className="bg-white rounded-xl border p-5 space-y-4">
            <div>
              <div className="text-lg font-semibold">{generator.label}</div>
              <div className="text-sm text-gray-500">Źródło: {generator.source}</div>
            </div>
            <div className="text-sm text-gray-600">
              Ostatnio dodano: <span className="font-semibold">{results[generator.key] ?? results[generator.source] ?? 0}</span>
            </div>
            <button
              onClick={() => runGenerator(generator)}
              disabled={loadingKey === generator.key}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
            >
              {loadingKey === generator.key ? 'Generuję...' : 'Generuj'}
            </button>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h2 className="font-semibold">Ostatnie wygenerowane leady</h2>
            <p className="text-xs text-gray-400 mt-1">Auto-odświeżanie co 30 sekund</p>
          </div>
          <button onClick={load} className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">Odśwież</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-4 py-3">Lead</th>
                <th className="text-left px-4 py-3">Firma</th>
                <th className="text-left px-4 py-3">Źródło</th>
                <th className="text-left px-4 py-3">Score</th>
                <th className="text-left px-4 py-3">Agent</th>
              </tr>
            </thead>
            <tbody>
              {leads.map(lead => (
                <tr key={lead.id} className="border-t">
                  <td className="px-4 py-3">
                    <div className="font-medium">{lead.full_name || `Lead #${lead.id}`}</div>
                    <div className="text-xs text-gray-400">{lead.email}</div>
                  </td>
                  <td className="px-4 py-3">{lead.company || '—'}</td>
                  <td className="px-4 py-3">{lead.source || '—'}</td>
                  <td className="px-4 py-3">{lead.score}</td>
                  <td className="px-4 py-3">{lead.assigned_to || '—'}</td>
                </tr>
              ))}
              {leads.length === 0 && (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-gray-400">Brak leadów do wyświetlenia.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

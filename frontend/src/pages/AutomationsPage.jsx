import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

const TRIGGER_LABELS = {
  new_lead: 'Nowy lead',
  stage_change: 'Zmiana etapu',
  score_above: 'Score powyżej progu',
  follow_up_due: 'Follow-up wymagany',
}
const ACTION_LABELS = {
  assign: 'Auto-przypisz',
  follow_up: 'Zaplanuj follow-up',
  close: 'Zamknij lead',
  notify: 'Wyślij powiadomienie',
}

export default function AutomationsPage() {
  const [automations, setAutomations] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', trigger: 'new_lead', action: 'assign', condition_json: '{}', enabled: true })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/automations')
      setAutomations(r.data)
    } catch { }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/automations', form)
      setShowForm(false)
      setForm({ name: '', trigger: 'new_lead', action: 'assign', condition_json: '{}', enabled: true })
      load()
    } catch { }
    setSaving(false)
  }

  const toggle = async (auto) => {
    try {
      await api.patch(`/automations/${auto.id}`, { enabled: !auto.enabled })
      load()
    } catch { }
  }

  const runNow = async (id) => {
    try {
      await api.post(`/automations/${id}/run`)
      load()
    } catch { }
  }

  const del = async (id) => {
    if (!window.confirm('Usuń automatyzację?')) return
    try { await api.delete(`/automations/${id}`); load() } catch { }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">⚡ Automatyzacje</h1>
          <p className="text-sm text-gray-500 mt-1">Reguły auto-przypisania, follow-up, zamykania leadów</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Nowa automatyzacja
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Dodaj automatyzację</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Nazwa *</label>
              <input required className="border rounded px-3 py-2 text-sm w-full" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Wyzwalacz</label>
              <select className="border rounded px-3 py-2 text-sm w-full" value={form.trigger} onChange={e => setForm(f => ({ ...f, trigger: e.target.value }))}>
                {Object.entries(TRIGGER_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Akcja</label>
              <select className="border rounded px-3 py-2 text-sm w-full" value={form.action} onChange={e => setForm(f => ({ ...f, action: e.target.value }))}>
                {Object.entries(ACTION_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            {form.trigger === 'score_above' && (
              <div>
                <label className="text-xs text-gray-500 block mb-1">Próg score (0-100)</label>
                <input type="number" min="0" max="100" className="border rounded px-3 py-2 text-sm w-full"
                  value={JSON.parse(form.condition_json || '{}').threshold || 70}
                  onChange={e => setForm(f => ({ ...f, condition_json: JSON.stringify({ threshold: parseInt(e.target.value) }) }))} />
              </div>
            )}
            <div className="flex items-center gap-2">
              <input type="checkbox" id="enabled" checked={form.enabled} onChange={e => setForm(f => ({ ...f, enabled: e.target.checked }))} className="rounded" />
              <label htmlFor="enabled" className="text-sm text-gray-600">Włączona</label>
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Zapisuję...' : 'Utwórz'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Anuluj</button>
            </div>
          </form>
        </div>
      )}

      <div className="space-y-3">
        {automations.map(a => (
          <div key={a.id} className={`bg-white rounded-xl border p-5 flex flex-col md:flex-row md:items-center gap-4 ${!a.enabled ? 'opacity-50' : ''}`}>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-800">{a.name}</span>
                {a.enabled
                  ? <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Aktywna</span>
                  : <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Wyłączona</span>
                }
              </div>
              <div className="text-sm text-gray-500 mt-1">
                <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs mr-2">{TRIGGER_LABELS[a.trigger] || a.trigger}</span>
                →
                <span className="bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-xs ml-2">{ACTION_LABELS[a.action] || a.action}</span>
              </div>
              {a.condition_json && a.condition_json !== '{}' && (
                <div className="text-xs text-gray-400 mt-1">Warunek: {a.condition_json}</div>
              )}
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              <span>Uruchomień: <strong>{a.runs}</strong></span>
              {a.last_run && <span>Ostatnie: {new Date(a.last_run).toLocaleDateString('pl-PL')}</span>}
            </div>
            <div className="flex gap-2">
              <button onClick={() => toggle(a)} className={`text-xs px-3 py-1.5 rounded-lg border ${a.enabled ? 'border-yellow-300 text-yellow-700 hover:bg-yellow-50' : 'border-green-300 text-green-700 hover:bg-green-50'}`}>
                {a.enabled ? 'Wyłącz' : 'Włącz'}
              </button>
              <button onClick={() => runNow(a.id)} className="text-xs px-3 py-1.5 rounded-lg border border-blue-300 text-blue-700 hover:bg-blue-50">
                ▶ Uruchom
              </button>
              <button onClick={() => del(a.id)} className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50">Usuń</button>
            </div>
          </div>
        ))}
        {automations.length === 0 && (
          <div className="text-center py-12 text-gray-400">Brak automatyzacji. Dodaj pierwszą!</div>
        )}
      </div>
    </div>
  )
}

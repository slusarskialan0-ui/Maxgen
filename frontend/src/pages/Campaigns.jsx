import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

const STATUS_COLORS = {
  aktywna: 'bg-green-100 text-green-700',
  zatrzymana: 'bg-yellow-100 text-yellow-700',
  zakonczona: 'bg-gray-100 text-gray-600',
}

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', source: '', budget: 0, target_leads: 0 })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await api.get('/campaigns')
      setCampaigns(r.data)
    } catch { }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/campaigns', { ...form, budget: parseFloat(form.budget) || 0, target_leads: parseInt(form.target_leads) || 0 })
      setShowForm(false)
      setForm({ name: '', description: '', source: '', budget: 0, target_leads: 0 })
      load()
    } catch { }
    setSaving(false)
  }

  const updateStatus = async (id, status) => {
    try {
      await api.patch(`/campaigns/${id}`, { status })
      load()
    } catch { }
  }

  const deleteCampaign = async (id) => {
    if (!window.confirm('Usuń kampanię?')) return
    try { await api.delete(`/campaigns/${id}`); load() } catch { }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">📣 Kampanie</h1>
          <p className="text-sm text-gray-500 mt-1">Zarządzaj kampaniami pozyskiwania leadów</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Nowa kampania
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Nowa kampania</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Nazwa *</label>
              <input required className="border rounded px-3 py-2 text-sm w-full" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Opis</label>
              <textarea className="border rounded px-3 py-2 text-sm w-full" rows={2} value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Źródło</label>
              <input className="border rounded px-3 py-2 text-sm w-full" value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} placeholder="np. Google Ads, Facebook" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Budżet (PLN)</label>
              <input type="number" min="0" className="border rounded px-3 py-2 text-sm w-full" value={form.budget} onChange={e => setForm(f => ({ ...f, budget: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Cel leadów</label>
              <input type="number" min="0" className="border rounded px-3 py-2 text-sm w-full" value={form.target_leads} onChange={e => setForm(f => ({ ...f, target_leads: e.target.value }))} />
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

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {campaigns.map(c => (
          <div key={c.id} className="bg-white rounded-xl border p-5 space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-semibold text-gray-800">{c.name}</h3>
                {c.source && <div className="text-xs text-gray-400 mt-0.5">{c.source}</div>}
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] || 'bg-gray-100 text-gray-600'}`}>{c.status}</span>
            </div>
            {c.description && <p className="text-sm text-gray-500">{c.description}</p>}
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-gray-50 rounded-lg p-2">
                <div className="text-lg font-bold text-blue-600">{c.current_leads}</div>
                <div className="text-xs text-gray-400">Leady</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-2">
                <div className="text-lg font-bold text-green-600">{c.won_leads}</div>
                <div className="text-xs text-gray-400">Wygrane</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-2">
                <div className="text-lg font-bold text-purple-600">{c.conversion_rate}%</div>
                <div className="text-xs text-gray-400">Konwersja</div>
              </div>
            </div>
            {c.target_leads > 0 && (
              <div>
                <div className="flex justify-between text-xs text-gray-400 mb-1">
                  <span>Postęp</span>
                  <span>{c.current_leads}/{c.target_leads}</span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2">
                  <div className="h-2 rounded-full bg-blue-500" style={{ width: `${Math.min(100, (c.current_leads / c.target_leads) * 100)}%` }} />
                </div>
              </div>
            )}
            <div className="flex gap-2 pt-1">
              <select
                className="border rounded text-xs px-2 py-1 flex-1"
                value={c.status}
                onChange={e => updateStatus(c.id, e.target.value)}
              >
                <option value="aktywna">Aktywna</option>
                <option value="zatrzymana">Zatrzymana</option>
                <option value="zakonczona">Zakończona</option>
              </select>
              <button onClick={() => deleteCampaign(c.id)} className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-2 py-1">Usuń</button>
            </div>
          </div>
        ))}
        {campaigns.length === 0 && (
          <div className="md:col-span-3 text-center py-12 text-gray-400">
            Brak kampanii. Utwórz pierwszą!
          </div>
        )}
      </div>
    </div>
  )
}

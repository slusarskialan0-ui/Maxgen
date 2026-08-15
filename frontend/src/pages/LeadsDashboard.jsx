import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line, CartesianGrid,
} from 'recharts'

const STAGE_COLORS = {
  nowy: '#3b82f6',
  kontakt: '#f59e0b',
  negocjacje: '#8b5cf6',
  wygrany: '#10b981',
  przegrany: '#ef4444',
}
const STAGE_LABELS = {
  nowy: 'Nowy',
  kontakt: 'Kontakt',
  negocjacje: 'Negocjacje',
  wygrany: 'Wygrany',
  przegrany: 'Przegrany',
}

function StatCard({ label, value, sub, color = 'blue' }) {
  const palette = {
    blue: 'bg-blue-50 border-blue-200 text-blue-700',
    green: 'bg-green-50 border-green-200 text-green-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    purple: 'bg-purple-50 border-purple-200 text-purple-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  }
  return (
    <div className={`rounded-xl border p-5 ${palette[color] || palette.blue}`}>
      <div className="text-3xl font-bold">{value}</div>
      <div className="text-sm mt-1 font-medium">{label}</div>
      {sub && <div className="text-xs mt-1 opacity-70">{sub}</div>}
    </div>
  )
}

function FunnelBar({ stage, count, pct, total }) {
  const color = STAGE_COLORS[stage] || '#6b7280'
  return (
    <div className="flex items-center gap-3 mb-2">
      <div className="w-28 text-sm text-right font-medium text-gray-600">{STAGE_LABELS[stage] || stage}</div>
      <div className="flex-1 bg-gray-100 rounded-full h-6 relative overflow-hidden">
        <div
          className="h-6 rounded-full flex items-center justify-end pr-2 text-white text-xs font-bold transition-all"
          style={{ width: `${Math.max(pct, 2)}%`, backgroundColor: color }}
        >
          {count}
        </div>
      </div>
      <div className="w-12 text-xs text-gray-500 text-right">{pct}%</div>
    </div>
  )
}

export default function LeadsDashboard() {
  const [leads, setLeads] = useState([])
  const [funnel, setFunnel] = useState({ stages: [], total: 0 })
  const [prediction, setPrediction] = useState(null)
  const [followUps, setFollowUps] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', company: '', industry: '', voivodeship: '', source: 'manual', notes: '' })
  const [saving, setSaving] = useState(false)
  const [filter, setFilter] = useState({ stage: '', source: '', assigned_to: '' })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [leadsRes, funnelRes, predRes, followRes] = await Promise.all([
        api.get('/leads', { params: { limit: 200, ...Object.fromEntries(Object.entries(filter).filter(([, v]) => v)) } }),
        api.get('/leads/funnel'),
        api.get('/leads/ai-prediction'),
        api.get('/leads/due-follow-ups'),
      ])
      setLeads(leadsRes.data.items || [])
      setFunnel(funnelRes.data)
      setPrediction(predRes.data)
      setFollowUps(followRes.data)
    } catch {
      // backend may not have these endpoints yet
    }
    setLoading(false)
  }, [filter])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/leads', form)
      setShowForm(false)
      setForm({ full_name: '', email: '', phone: '', company: '', industry: '', voivodeship: '', source: 'manual', notes: '' })
      load()
    } catch { }
    setSaving(false)
  }

  const updateStage = async (leadId, stage) => {
    try {
      await api.patch(`/leads/${leadId}`, { stage })
      load()
    } catch { }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  const bySource = leads.reduce((acc, l) => { acc[l.source] = (acc[l.source] || 0) + 1; return acc }, {})
  const sourceData = Object.entries(bySource).map(([source, count]) => ({ source, count }))

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">🎯 Leads Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Panel sprzedażowy — lejek, scoring AI, follow-upy</p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          + Nowy lead
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Wszystkie leady" value={funnel.total} color="blue" />
        <StatCard label="Śr. score AI" value={prediction?.avg_score ?? '—'} sub="0–100" color="purple" />
        <StatCard label="Konwersja pred." value={`${prediction?.avg_conversion_pct ?? 0}%`} color="green" />
        <StatCard label="Follow-up dziś" value={followUps.length} color="yellow" />
      </div>

      {/* Add lead form */}
      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Dodaj nowego leada</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              ['full_name', 'Imię i nazwisko'],
              ['email', 'E-mail'],
              ['phone', 'Telefon'],
              ['company', 'Firma'],
              ['industry', 'Branża'],
              ['voivodeship', 'Województwo'],
            ].map(([key, label]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 block mb-1">{label}</label>
                <input
                  className="border rounded px-3 py-2 text-sm w-full"
                  value={form[key]}
                  onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Źródło</label>
              <select className="border rounded px-3 py-2 text-sm w-full" value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))}>
                {['manual', 'webhook', 'form', 'import', 'social', 'referral'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 block mb-1">Notatki</label>
              <textarea className="border rounded px-3 py-2 text-sm w-full" rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Zapisuję...' : 'Dodaj leada'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Anuluj</button>
            </div>
          </form>
        </div>
      )}

      {/* Funnel */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">🏆 Lejek sprzedażowy</h2>
        {funnel.stages.map(s => (
          <FunnelBar key={s.stage} {...s} />
        ))}
        {funnel.stages.length === 0 && <p className="text-gray-400 text-sm">Brak danych</p>}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Leady wg źródła</h2>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={sourceData} dataKey="count" nameKey="source" cx="50%" cy="50%" outerRadius={80} label={({ source }) => source}>
                  {sourceData.map((_, i) => <Cell key={i} fill={Object.values(STAGE_COLORS)[i % 5]} />)}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-gray-400 text-sm">Brak danych</p>}
        </div>

        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">🤖 AI — Top leady do obsługi</h2>
          {prediction?.top_leads?.length ? (
            <div className="space-y-2">
              {prediction.top_leads.slice(0, 5).map(l => (
                <div key={l.id} className="flex items-center justify-between p-2 rounded-lg bg-gray-50 text-sm">
                  <div>
                    <span className="font-medium">{l.full_name || l.company || `Lead #${l.id}`}</span>
                    <span className="text-xs text-gray-400 ml-2">{l.stage}</span>
                  </div>
                  <div className="flex gap-2 items-center">
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">score: {l.score}</span>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">{Math.round((l.conversion_probability || 0) * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-gray-400 text-sm">Brak leadów</p>}
        </div>
      </div>

      {/* Follow-ups due */}
      {followUps.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <h2 className="font-semibold mb-3 text-yellow-800">⏰ Follow-upy do wykonania ({followUps.length})</h2>
          <div className="space-y-2">
            {followUps.slice(0, 5).map(l => (
              <div key={l.id} className="flex items-center justify-between bg-white rounded-lg p-3 text-sm">
                <div>
                  <span className="font-medium">{l.full_name || l.company || `Lead #${l.id}`}</span>
                  <span className="text-xs text-gray-400 ml-2">{l.email}</span>
                </div>
                <span className="text-xs text-yellow-600">{l.follow_up_at ? new Date(l.follow_up_at).toLocaleDateString('pl-PL') : ''}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl border p-4 flex flex-wrap gap-3 items-center">
        <span className="text-sm font-medium text-gray-600">Filtry:</span>
        <select className="border rounded px-3 py-1.5 text-sm" value={filter.stage} onChange={e => setFilter(f => ({ ...f, stage: e.target.value }))}>
          <option value="">Wszystkie etapy</option>
          {Object.entries(STAGE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="border rounded px-3 py-1.5 text-sm" value={filter.source} onChange={e => setFilter(f => ({ ...f, source: e.target.value }))}>
          <option value="">Wszystkie źródła</option>
          {['manual', 'webhook', 'form', 'import', 'social', 'referral'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <button onClick={load} className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">Odśwież</button>
      </div>

      {/* Leads table */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">Lista leadów ({leads.length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Lead</th>
                <th className="px-4 py-3 text-left">Firma</th>
                <th className="px-4 py-3 text-left">Etap</th>
                <th className="px-4 py-3 text-left">Score</th>
                <th className="px-4 py-3 text-left">Przypisany</th>
                <th className="px-4 py-3 text-left">Źródło</th>
                <th className="px-4 py-3 text-left">Akcje</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {leads.slice(0, 50).map(l => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{l.full_name || `Lead #${l.id}`}</div>
                    <div className="text-xs text-gray-400">{l.email}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{l.company || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium" style={{ backgroundColor: STAGE_COLORS[l.stage] + '20', color: STAGE_COLORS[l.stage] }}>
                      {STAGE_LABELS[l.stage] || l.stage}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-purple-500" style={{ width: `${l.score}%` }} />
                      </div>
                      <span className="text-xs text-gray-500">{l.score}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{l.assigned_to || '—'}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{l.source}</td>
                  <td className="px-4 py-3">
                    <select
                      className="border rounded text-xs px-2 py-1"
                      value={l.stage}
                      onChange={e => updateStage(l.id, e.target.value)}
                    >
                      {Object.entries(STAGE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {leads.length === 0 && (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Brak leadów. Dodaj pierwszy lub uruchom pipeline.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

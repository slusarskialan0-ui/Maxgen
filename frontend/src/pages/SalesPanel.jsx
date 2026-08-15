import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function SalesPanel() {
  const [payments, setPayments] = useState([])
  const [funnel, setFunnel] = useState({ stages: [], total: 0 })
  const [metrics, setMetrics] = useState(null)
  const [revenue, setRevenue] = useState({ total_revenue: 0, by_month: [] })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ amount: 0, status: 'pending', method: 'offline_transfer', offer_id: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [payRes, funnelRes, metricsRes, revenueRes] = await Promise.all([
        api.get('/payments'),
        api.get('/leads/funnel'),
        api.get('/metrics'),
        api.get('/analytics/revenue'),
      ])
      setPayments(payRes.data || [])
      setFunnel(funnelRes.data || { stages: [], total: 0 })
      setMetrics(metricsRes.data || null)
      setRevenue(revenueRes.data || { total_revenue: 0, by_month: [] })
    } catch {
      setError('Nie udało się pobrać danych sprzedażowych.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const createPayment = async (e) => {
    e.preventDefault()
    try {
      await api.post('/payments', {
        amount: parseFloat(form.amount) || 0,
        status: form.status,
        method: form.method,
        offer_id: form.offer_id ? parseInt(form.offer_id) : null,
      })
      setForm({ amount: 0, status: 'pending', method: 'offline_transfer', offer_id: '' })
      load()
    } catch {
      setError('Nie udało się utworzyć płatności.')
    }
  }

  const simulate = async (id) => {
    try {
      await api.post(`/payments/${id}/simulate`)
      load()
    } catch {
      setError('Nie udało się zasymulować płatności.')
    }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  const traffic = metrics?.pipeline_found || 0
  const conversions = (funnel.stages || []).find(s => s.stage === 'wygrany')?.count || 0
  const conversionRate = traffic ? Math.round((conversions / traffic) * 1000) / 10 : 0

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">💼 Panel sprzedaży</h1>
        <p className="text-sm text-gray-500 mt-1">Dashboard konwersji, ruchu i przychodów + płatności offline</p>
      </div>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs text-gray-500">Ruch (pipeline found)</div>
          <div className="text-3xl font-bold text-blue-600">{traffic}</div>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs text-gray-500">Konwersja</div>
          <div className="text-3xl font-bold text-green-600">{conversionRate}%</div>
        </div>
        <div className="rounded-xl border bg-white p-5">
          <div className="text-xs text-gray-500">Przychód</div>
          <div className="text-3xl font-bold text-purple-600">{(revenue.total_revenue || 0).toFixed(2)} PLN</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Przychód miesięczny</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={revenue.by_month || []}>
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="revenue" fill="#8b5cf6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Nowa płatność offline</h2>
        <form onSubmit={createPayment} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input type="number" min="0" required className="border rounded px-3 py-2 text-sm" placeholder="Kwota" value={form.amount} onChange={e => setForm(v => ({ ...v, amount: e.target.value }))} />
          <input className="border rounded px-3 py-2 text-sm" placeholder="Offer ID (opcjonalnie)" value={form.offer_id} onChange={e => setForm(v => ({ ...v, offer_id: e.target.value }))} />
          <select className="border rounded px-3 py-2 text-sm" value={form.method} onChange={e => setForm(v => ({ ...v, method: e.target.value }))}>
            <option value="offline_transfer">offline_transfer</option>
            <option value="cash">cash</option>
            <option value="invoice">invoice</option>
          </select>
          <select className="border rounded px-3 py-2 text-sm" value={form.status} onChange={e => setForm(v => ({ ...v, status: e.target.value }))}>
            <option value="pending">pending</option>
            <option value="confirmed">confirmed</option>
            <option value="failed">failed</option>
          </select>
          <button className="md:col-span-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Dodaj płatność</button>
        </form>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">ID</th>
              <th className="px-4 py-3 text-left">Kwota</th>
              <th className="px-4 py-3 text-left">Metoda</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Potwierdzenie</th>
              <th className="px-4 py-3 text-left">Akcja</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {payments.map(p => (
              <tr key={p.id}>
                <td className="px-4 py-3">#{p.id}</td>
                <td className="px-4 py-3">{p.amount} {p.currency}</td>
                <td className="px-4 py-3">{p.method}</td>
                <td className="px-4 py-3">{p.status}</td>
                <td className="px-4 py-3 text-xs">{p.confirmation_code || '—'}</td>
                <td className="px-4 py-3">
                  <button onClick={() => simulate(p.id)} className="text-xs px-2 py-1 border rounded hover:bg-gray-50">Symuluj</button>
                </td>
              </tr>
            ))}
            {payments.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Brak płatności</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

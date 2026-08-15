import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

export default function PaymentsPage() {
  const [payments, setPayments] = useState([])
  const [leads, setLeads] = useState([])
  const [form, setForm] = useState({ lead_id: '', amount: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [p, l] = await Promise.all([api.get('/payments'), api.get('/leads', { params: { limit: 300 } })])
      setPayments(p.data || [])
      setLeads(l.data?.items || [])
    } catch { setError('Nie udało się pobrać danych.') }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const simulate = async (e) => {
    e.preventDefault()
    if (!form.lead_id || !form.amount) return
    setError('')
    try {
      await api.post('/payments/simulate', { lead_id: Number(form.lead_id), amount: Number(form.amount) })
      setForm({ lead_id: '', amount: '' })
      load()
    } catch { setError('Nie udało się zasymulować płatności.') }
  }

  const updateStatus = async (id, status) => {
    setError('')
    try { await api.patch(`/payments/${id}`, { status }); load() } catch { setError('Nie udało się zaktualizować płatności.') }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">💳 Płatności offline</h1>
        <p className="text-sm text-gray-500 mt-1">Symulacja transakcji i potwierdzeń</p>
      </div>

      {error && (<div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">{error}</div>)}

      <div className="bg-white border rounded-xl p-6">
        <form onSubmit={simulate} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Lead</label>
            <select className="border rounded px-3 py-2 text-sm w-full" value={form.lead_id} onChange={e => setForm(f => ({ ...f, lead_id: e.target.value }))}>
              <option value="">Wybierz lead</option>
              {leads.map(l => <option key={l.id} value={l.id}>{l.full_name || l.company || `Lead #${l.id}`}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Kwota</label>
            <input type="number" min="1" className="border rounded px-3 py-2 text-sm w-full" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
          </div>
          <button className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">Symuluj płatność</button>
        </form>
      </div>

      <div className="bg-white border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">ID</th>
              <th className="px-4 py-3 text-left">Lead</th>
              <th className="px-4 py-3 text-left">Kwota</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Kod</th>
              <th className="px-4 py-3 text-left">Akcja</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {payments.map(p => (
              <tr key={p.id}>
                <td className="px-4 py-3">#{p.id}</td>
                <td className="px-4 py-3">{p.lead_id}</td>
                <td className="px-4 py-3">{p.amount} PLN</td>
                <td className="px-4 py-3">{p.status}</td>
                <td className="px-4 py-3 text-xs">{p.confirmation_code || '—'}</td>
                <td className="px-4 py-3">
                  <select className="border rounded text-xs px-2 py-1" value={p.status} onChange={e => updateStatus(p.id, e.target.value)}>
                    {['pending', 'confirmed', 'failed', 'refunded'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
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

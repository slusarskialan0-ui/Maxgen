import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

export default function OffersPage() {
  const [offers, setOffers] = useState([])
  const [leads, setLeads] = useState([])
  const [form, setForm] = useState({ lead_id: '', amount: '' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [o, l] = await Promise.all([api.get('/offers'), api.get('/leads', { params: { limit: 300 } })])
      setOffers(o.data || [])
      setLeads(l.data?.items || [])
    } catch { setError('Nie udało się pobrać danych.') }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const createOffer = async (e) => {
    e.preventDefault()
    if (!form.lead_id) return
    setError('')
    try {
      await api.post('/offers', { lead_id: Number(form.lead_id), amount: form.amount ? Number(form.amount) : undefined })
      setForm({ lead_id: '', amount: '' })
      load()
    } catch { setError('Nie udało się wygenerować oferty.') }
  }

  const updateStatus = async (id, status) => {
    setError('')
    try { await api.patch(`/offers/${id}`, { status }); load() } catch { setError('Nie udało się zaktualizować oferty.') }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">📄 Oferty offline</h1>
        <p className="text-sm text-gray-500 mt-1">Generator i zarządzanie ofertami sprzedażowymi</p>
      </div>

      {error && (<div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3">{error}</div>)}

      <div className="bg-white border rounded-xl p-6">
        <form onSubmit={createOffer} className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Lead</label>
            <select className="border rounded px-3 py-2 text-sm w-full" value={form.lead_id} onChange={e => setForm(f => ({ ...f, lead_id: e.target.value }))}>
              <option value="">Wybierz lead</option>
              {leads.map(l => <option key={l.id} value={l.id}>{l.full_name || l.company || `Lead #${l.id}`}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Kwota (opcjonalnie)</label>
            <input type="number" min="0" className="border rounded px-3 py-2 text-sm w-full" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
          </div>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Wygeneruj ofertę</button>
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
              <th className="px-4 py-3 text-left">Akcja</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {offers.map(o => (
              <tr key={o.id}>
                <td className="px-4 py-3">#{o.id}</td>
                <td className="px-4 py-3">{o.lead_id}</td>
                <td className="px-4 py-3">{o.amount} PLN</td>
                <td className="px-4 py-3">{o.status}</td>
                <td className="px-4 py-3">
                  <select className="border rounded text-xs px-2 py-1" value={o.status} onChange={e => updateStatus(o.id, e.target.value)}>
                    {['draft', 'sent', 'accepted', 'rejected'].map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </td>
              </tr>
            ))}
            {offers.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Brak ofert</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

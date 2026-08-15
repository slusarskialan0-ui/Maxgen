import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

export default function OffersPanel() {
  const [offers, setOffers] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ title: '', amount: 0, status: 'draft', lead_id: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const r = await api.get('/offers')
      setOffers(r.data || [])
    } catch {
      setError('Nie udało się pobrać ofert.')
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const createOffer = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.post('/offers', {
        title: form.title,
        amount: parseFloat(form.amount) || 0,
        status: form.status,
        lead_id: form.lead_id ? parseInt(form.lead_id) : null,
      })
      setForm({ title: '', amount: 0, status: 'draft', lead_id: '' })
      load()
    } catch {
      setError('Nie udało się utworzyć oferty.')
    }
    setSaving(false)
  }

  const updateStatus = async (id, status) => {
    try {
      await api.patch(`/offers/${id}`, { status })
      load()
    } catch {
      setError('Nie udało się zaktualizować statusu oferty.')
    }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">🧾 Panel ofert</h1>
        <p className="text-sm text-gray-500 mt-1">Oferty handlowe: draft, wysyłka, akceptacja</p>
      </div>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Nowa oferta</h2>
        <form onSubmit={createOffer} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <input required className="border rounded px-3 py-2 text-sm" placeholder="Tytuł oferty" value={form.title} onChange={e => setForm(v => ({ ...v, title: e.target.value }))} />
          <input type="number" min="0" className="border rounded px-3 py-2 text-sm" placeholder="Kwota" value={form.amount} onChange={e => setForm(v => ({ ...v, amount: e.target.value }))} />
          <input className="border rounded px-3 py-2 text-sm" placeholder="Lead ID (opcjonalnie)" value={form.lead_id} onChange={e => setForm(v => ({ ...v, lead_id: e.target.value }))} />
          <select className="border rounded px-3 py-2 text-sm" value={form.status} onChange={e => setForm(v => ({ ...v, status: e.target.value }))}>
            <option value="draft">draft</option>
            <option value="sent">sent</option>
            <option value="accepted">accepted</option>
            <option value="rejected">rejected</option>
          </select>
          <button disabled={saving} className="md:col-span-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Zapisuję...' : 'Utwórz ofertę'}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">ID</th>
              <th className="px-4 py-3 text-left">Tytuł</th>
              <th className="px-4 py-3 text-left">Kwota</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Akcja</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {offers.map(o => (
              <tr key={o.id}>
                <td className="px-4 py-3">#{o.id}</td>
                <td className="px-4 py-3">{o.title}</td>
                <td className="px-4 py-3">{o.amount} {o.currency}</td>
                <td className="px-4 py-3">{o.status}</td>
                <td className="px-4 py-3">
                  <select className="border rounded px-2 py-1 text-xs" value={o.status} onChange={e => updateStatus(o.id, e.target.value)}>
                    {['draft', 'sent', 'accepted', 'rejected', 'expired'].map(s => <option key={s} value={s}>{s}</option>)}
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

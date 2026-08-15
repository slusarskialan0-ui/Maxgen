import React, { useEffect, useState } from 'react'
import api from '../api/api'

export default function OffersPanel() {
  const [offers, setOffers] = useState([])
  const [form, setForm] = useState({ lead_id: '', title: '', amount: 0 })
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const r = await api.get('/offers')
      setOffers(r.data)
    } catch { }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const createOffer = async (e) => {
    e.preventDefault()
    try {
      await api.post('/offers', {
        lead_id: parseInt(form.lead_id),
        title: form.title,
        amount: parseFloat(form.amount) || 0,
        description: 'Oferta utworzona z panelu ofert',
      })
      setForm({ lead_id: '', title: '', amount: 0 })
      load()
    } catch { }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">🧾 Panel ofert</h1>
      <form onSubmit={createOffer} className="bg-white rounded-xl border p-4 grid grid-cols-1 md:grid-cols-4 gap-3">
        <input className="border rounded px-3 py-2 text-sm" placeholder="Lead ID" value={form.lead_id} onChange={e => setForm(f => ({ ...f, lead_id: e.target.value }))} required />
        <input className="border rounded px-3 py-2 text-sm" placeholder="Tytuł oferty" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
        <input className="border rounded px-3 py-2 text-sm" type="number" placeholder="Kwota" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
        <button className="bg-blue-600 text-white rounded px-3 py-2 text-sm hover:bg-blue-700">Dodaj ofertę</button>
      </form>
      <div className="bg-white rounded-xl border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500">
            <tr>
              <th className="px-4 py-3 text-left">ID</th>
              <th className="px-4 py-3 text-left">Lead</th>
              <th className="px-4 py-3 text-left">Tytuł</th>
              <th className="px-4 py-3 text-left">Kwota</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {offers.map(o => (
              <tr key={o.id} className="border-t">
                <td className="px-4 py-3">{o.id}</td>
                <td className="px-4 py-3">{o.lead_id}</td>
                <td className="px-4 py-3">{o.title}</td>
                <td className="px-4 py-3">{o.amount} {o.currency}</td>
                <td className="px-4 py-3">{o.status}</td>
              </tr>
            ))}
            {offers.length === 0 && <tr><td className="px-4 py-8 text-center text-gray-400" colSpan={5}>Brak ofert</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

import React, { useEffect, useState } from 'react'
import api from '../api/api'

export default function SalesPanel() {
  const [leads, setLeads] = useState([])
  const [payments, setPayments] = useState([])

  useEffect(() => {
    Promise.all([
      api.get('/leads', { params: { limit: 100 } }),
      api.get('/payments'),
    ]).then(([leadsRes, paymentsRes]) => {
      setLeads(leadsRes.data.items || [])
      setPayments(paymentsRes.data || [])
    }).catch(() => {})
  }, [])

  const won = leads.filter(l => l.stage === 'wygrany').length
  const open = leads.filter(l => !['wygrany', 'przegrany'].includes(l.stage)).length
  const confirmedPayments = payments.filter(p => p.status === 'confirmed').length

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">💼 Panel sprzedaży</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border bg-blue-50 p-5"><div className="text-3xl font-bold text-blue-700">{open}</div><div className="text-sm text-blue-700">Aktywne leady</div></div>
        <div className="rounded-xl border bg-green-50 p-5"><div className="text-3xl font-bold text-green-700">{won}</div><div className="text-sm text-green-700">Wygrane leady</div></div>
        <div className="rounded-xl border bg-purple-50 p-5"><div className="text-3xl font-bold text-purple-700">{confirmedPayments}</div><div className="text-sm text-purple-700">Potwierdzone płatności</div></div>
      </div>
      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold mb-3">Nadchodzące follow-upy</h2>
        <ul className="space-y-2 text-sm">
          {leads.filter(l => l.follow_up_at).slice(0, 10).map(l => (
            <li key={l.id} className="flex justify-between border-b pb-2">
              <span>{l.full_name || l.company || `Lead #${l.id}`}</span>
              <span className="text-gray-500">{new Date(l.follow_up_at).toLocaleString('pl-PL')}</span>
            </li>
          ))}
          {leads.filter(l => l.follow_up_at).length === 0 && <li className="text-gray-400">Brak follow-upów</li>}
        </ul>
      </div>
    </div>
  )
}

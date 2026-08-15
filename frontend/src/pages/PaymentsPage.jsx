import React, { useCallback, useEffect, useState } from 'react'
import api from '../api/api'

const STATUS_STYLES = {
  oczekuje: 'bg-yellow-100 text-yellow-700',
  potwierdzona: 'bg-green-100 text-green-700',
  odrzucona: 'bg-red-100 text-red-700',
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState([])
  const [stats, setStats] = useState({ total: 0, confirmed: 0, rejected: 0, total_amount: 0 })
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ lead_id: '', amount: 1000, method: 'przelew', description: 'Płatność testowa offline' })

  const load = useCallback(async () => {
    try {
      const [paymentsRes, statsRes] = await Promise.all([api.get('/payments'), api.get('/payments/stats')])
      setPayments(paymentsRes.data || [])
      setStats(statsRes.data || { total: 0, confirmed: 0, rejected: 0, total_amount: 0 })
    } catch { }
  }, [])

  useEffect(() => { load() }, [load])

  const createPayment = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/payments', {
        lead_id: form.lead_id ? Number(form.lead_id) : null,
        amount: Number(form.amount),
        currency: 'PLN',
        method: form.method,
        description: form.description,
      })
      setShowForm(false)
      setForm({ lead_id: '', amount: 1000, method: 'przelew', description: 'Płatność testowa offline' })
      load()
    } catch { }
    setSaving(false)
  }

  const updateStatus = async (id, action) => {
    try {
      await api.patch(`/payments/${id}/${action}`)
      load()
    } catch { }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">💳 Płatności offline</h1>
          <p className="text-sm text-gray-500 mt-1">Symulacja płatności, potwierdzeń i odrzuceń w PLN.</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          Dodaj płatność testową
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border p-5"><div className="text-3xl font-bold">{stats.total}</div><div className="text-sm text-gray-500 mt-1">Wszystkie</div></div>
        <div className="bg-white rounded-xl border p-5"><div className="text-3xl font-bold text-green-600">{stats.confirmed}</div><div className="text-sm text-gray-500 mt-1">Potwierdzone</div></div>
        <div className="bg-white rounded-xl border p-5"><div className="text-3xl font-bold text-red-600">{stats.rejected}</div><div className="text-sm text-gray-500 mt-1">Odrzucone</div></div>
        <div className="bg-white rounded-xl border p-5"><div className="text-3xl font-bold">{Number(stats.total_amount || 0).toFixed(2)} PLN</div><div className="text-sm text-gray-500 mt-1">Łączna kwota</div></div>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Nowa płatność testowa</h2>
          <form onSubmit={createPayment} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Lead ID (opcjonalnie)</label>
              <input className="border rounded px-3 py-2 text-sm w-full" value={form.lead_id} onChange={e => setForm(f => ({ ...f, lead_id: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Kwota</label>
              <input type="number" min="1" step="0.01" className="border rounded px-3 py-2 text-sm w-full" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Metoda</label>
              <select className="border rounded px-3 py-2 text-sm w-full" value={form.method} onChange={e => setForm(f => ({ ...f, method: e.target.value }))}>
                {['przelew', 'karta', 'blik', 'gotówka'].map(method => <option key={method} value={method}>{method}</option>)}
              </select>
            </div>
            <div className="md:col-span-4">
              <label className="text-xs text-gray-500 block mb-1">Opis</label>
              <input className="border rounded px-3 py-2 text-sm w-full" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="md:col-span-4 flex gap-3">
              <button type="submit" disabled={saving} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50">
                {saving ? 'Zapisywanie...' : 'Zapisz płatność'}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Anuluj</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold">Lista płatności</h2>
          <button onClick={load} className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">Odśwież</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Lead</th>
                <th className="text-left px-4 py-3">Kwota</th>
                <th className="text-left px-4 py-3">Metoda</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Opis</th>
                <th className="text-left px-4 py-3">Akcje</th>
              </tr>
            </thead>
            <tbody>
              {payments.map(payment => (
                <tr key={payment.id} className="border-t">
                  <td className="px-4 py-3 font-medium">#{payment.id}</td>
                  <td className="px-4 py-3">{payment.lead_id || '—'}</td>
                  <td className="px-4 py-3">{Number(payment.amount || 0).toFixed(2)} {payment.currency}</td>
                  <td className="px-4 py-3">{payment.method}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[payment.status] || 'bg-gray-100 text-gray-700'}`}>
                      {payment.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">{payment.description || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => updateStatus(payment.id, 'confirm')}
                        disabled={payment.status === 'potwierdzona'}
                        className="px-2 py-1 rounded border border-green-300 text-green-700 text-xs hover:bg-green-50 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Potwierdź
                      </button>
                      <button
                        onClick={() => updateStatus(payment.id, 'reject')}
                        disabled={payment.status === 'odrzucona'}
                        className="px-2 py-1 rounded border border-red-300 text-red-700 text-xs hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Odrzuć
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr>
                  <td colSpan="7" className="px-4 py-8 text-center text-gray-400">Brak płatności.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

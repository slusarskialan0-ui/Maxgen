import React, { useEffect, useState } from 'react'
import api from '../api/api'

const currency = (value) => `${(value || 0).toLocaleString('pl-PL')} zł`

export default function AutoControlCenter() {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [message, setMessage] = useState('')

  const refresh = async () => {
    setLoading(true)
    try {
      const response = await api.get('/auto/overview')
      setOverview(response.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh().catch(() => setLoading(false))
  }, [])

  const runAction = async (label, request) => {
    setBusy(label)
    setMessage('')
    try {
      const response = await request()
      setMessage(`${label}: ${response.data.status || 'ok'}`)
      await refresh()
    } catch {
      setMessage(`${label}: błąd wykonania`)
    } finally {
      setBusy('')
    }
  }

  const leads = overview?.sales?.items || []
  const campaigns = overview?.campaigns?.items || []
  const offers = overview?.offers?.items || []
  const payments = overview?.payments?.items || []
  const logs = overview?.automations?.logs || []
  const automations = overview?.automations?.automations || []

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold">🤖 AUTO CONTROL CENTER</h1>
          <p className="mt-1 text-sm text-gray-500">Kompletny lokalny system leadów, sprzedaży, ofert, kampanii, płatności i backupów bez API.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={() => runAction('Bootstrap', () => api.post('/auto/bootstrap'))} className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Bootstrap</button>
          <button onClick={() => runAction('Leady', () => api.post('/auto/leads/generate', { voivodeship: 'mazowieckie', industries: ['mechanik', 'dealer samochodowy', 'wulkanizacja'], limit: 12 }))} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Generuj leady</button>
          <button onClick={() => runAction('Sprzedaż', () => api.post('/auto/sales/run'))} className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white">Uruchom sprzedaż</button>
          <button onClick={() => runAction('Kampanie', () => api.post('/auto/campaigns/generate'))} className="rounded-xl bg-fuchsia-600 px-4 py-2 text-sm font-semibold text-white">Generuj kampanie</button>
          <button onClick={() => runAction('Płatności', () => api.post('/auto/payments/simulate'))} className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-900">Symuluj płatności</button>
          <button onClick={() => runAction('Backup', () => api.post('/auto/sync/backup'))} className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700">Backup</button>
          <button onClick={() => runAction('Recovery', () => api.post('/auto/sync/recovery'))} className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700">Recovery</button>
        </div>
      </div>

      {message && <div className="rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700">{busy ? `${busy}...` : message}</div>}

      <div className="grid grid-cols-2 gap-4 xl:grid-cols-7">
        {Object.entries(overview?.counts || {}).map(([key, value]) => (
          <div key={key} className="rounded-2xl border bg-white p-4">
            <div className="text-xs uppercase tracking-wide text-gray-500">{key}</div>
            <div className="mt-2 text-2xl font-bold text-slate-900">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Panel leadów</h2>
          <p className="mt-1 text-sm text-gray-500">Generator leadów lokalnych, ruchu i scoringu AI offline.</p>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-xl bg-blue-50 p-4 text-blue-700">Leads total<br /><span className="text-2xl font-bold">{overview?.conversion?.total_leads || 0}</span></div>
            <div className="rounded-xl bg-indigo-50 p-4 text-indigo-700">Qualified rate<br /><span className="text-2xl font-bold">{overview?.conversion?.qualification_rate_pct || 0}%</span></div>
          </div>
          <div className="mt-4 space-y-3">
            {leads.slice(0, 5).map((lead) => (
              <div key={lead.id} className="rounded-xl border p-4 text-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-semibold">{lead.company_name}</div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">{lead.offline_ai_score}/100</span>
                </div>
                <div className="mt-2 text-gray-500">{lead.industry} · {lead.city || lead.voivodeship} · {lead.source_type}</div>
                <div className="mt-2 text-xs text-gray-600">{lead.generated_content}</div>
              </div>
            ))}
            {!loading && leads.length === 0 && <div className="rounded-xl bg-gray-50 p-4 text-sm text-gray-500">Najpierw uruchom bootstrap i generowanie leadów.</div>}
          </div>
        </section>

        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Panel sprzedaży</h2>
          <p className="mt-1 text-sm text-gray-500">Kwalifikacja, etapy lejka, auto-przypisanie, follow-up i auto-zamykanie leadów.</p>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            {Object.entries(overview?.sales?.stages || {}).map(([stage, count]) => (
              <div key={stage} className="rounded-xl bg-emerald-50 p-4 text-emerald-700">
                {stage}<br /><span className="text-2xl font-bold">{count}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
            Close rate: <span className="font-bold">{overview?.conversion?.close_rate_pct || 0}%</span> · Won leads: <span className="font-bold">{overview?.conversion?.won_leads || 0}</span>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            {automations.filter((item) => item.automation_type === 'sales').map((item) => (
              <div key={item.id} className="rounded-xl border p-4">
                <div className="font-semibold">{item.summary || 'Sprzedaż offline'}</div>
                <div className="mt-1 text-gray-500">Recovery: {item.recovery_action || 'n/a'}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Panel kampanii</h2>
          <p className="mt-1 text-sm text-gray-500">Offline generator kampanii, opisów, CTA i treści reklamowych.</p>
          <div className="mt-4 space-y-3">
            {campaigns.map((campaign) => (
              <div key={campaign.id} className="rounded-xl border p-4 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">{campaign.name}</div>
                  <span className="rounded-full bg-fuchsia-100 px-3 py-1 text-xs text-fuchsia-700">{campaign.channel}</span>
                </div>
                <div className="mt-2 text-gray-500">{campaign.description}</div>
                <div className="mt-2 text-xs text-gray-600">CTA: {campaign.cta}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Panel ofert</h2>
          <p className="mt-1 text-sm text-gray-500">Oferty i treści sprzedażowe generowane lokalnie dla zamknięcia sprzedaży.</p>
          <div className="mt-4 space-y-3">
            {offers.map((offer) => (
              <div key={offer.id} className="rounded-xl border p-4 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">{offer.title}</div>
                  <span className="rounded-full bg-amber-100 px-3 py-1 text-xs text-amber-700">{currency(offer.price)}</span>
                </div>
                <div className="mt-2 text-gray-500">{offer.summary}</div>
                <div className="mt-2 text-xs text-gray-600">{offer.sales_copy}</div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Dashboard konwersji</h2>
          <div className="mt-4 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-4">Qualified<br /><span className="text-2xl font-bold">{overview?.conversion?.qualified_leads || 0}</span></div>
            <div className="rounded-xl bg-slate-50 p-4">Offers<br /><span className="text-2xl font-bold">{overview?.conversion?.offers_generated || 0}</span></div>
            <div className="rounded-xl bg-slate-50 p-4">Won<br /><span className="text-2xl font-bold">{overview?.conversion?.won_leads || 0}</span></div>
            <div className="rounded-xl bg-slate-50 p-4">Paid<br /><span className="text-2xl font-bold">{overview?.conversion?.confirmed_payments || 0}</span></div>
          </div>
        </section>

        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Dashboard przychodów</h2>
          <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
            <div className="rounded-xl bg-emerald-50 p-4 text-emerald-700">Revenue<br /><span className="text-2xl font-bold">{currency(overview?.revenue?.total_revenue)}</span></div>
            <div className="rounded-xl bg-blue-50 p-4 text-blue-700">Pipeline<br /><span className="text-2xl font-bold">{currency(overview?.revenue?.pipeline_value)}</span></div>
            <div className="rounded-xl bg-amber-50 p-4 text-amber-700">Pending<br /><span className="text-2xl font-bold">{currency(overview?.revenue?.pending_revenue)}</span></div>
          </div>
          <div className="mt-4 space-y-2 text-sm">
            {(overview?.revenue?.by_month || []).map((item) => (
              <div key={item.month} className="flex items-center justify-between rounded-xl border px-4 py-3">
                <span>{item.month}</span>
                <span className="font-semibold text-emerald-600">{currency(item.revenue)}</span>
              </div>
            ))}
            {!loading && (overview?.revenue?.by_month || []).length === 0 && <div className="rounded-xl bg-gray-50 p-4 text-gray-500">Brak potwierdzonych płatności — uruchom symulację płatności.</div>}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Płatności offline</h2>
          <div className="mt-4 space-y-3">
            {payments.map((payment) => (
              <div key={payment.id} className="rounded-xl border p-4 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">{payment.confirmation_code}</div>
                  <span className={`rounded-full px-3 py-1 text-xs ${payment.status === 'confirmed' ? 'bg-emerald-100 text-emerald-700' : payment.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-rose-100 text-rose-700'}`}>{payment.status}</span>
                </div>
                <div className="mt-2 text-gray-500">{currency(payment.amount)} · {payment.method}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border bg-white p-6">
          <h2 className="text-lg font-semibold">Automatyzacje, backup i recovery</h2>
          <div className="mt-4 space-y-3">
            {automations.map((item) => (
              <div key={item.id} className="rounded-xl border p-4 text-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold">{item.automation_type}</div>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs">{item.status}</span>
                </div>
                <div className="mt-1 text-gray-500">{item.summary}</div>
                <div className="mt-1 text-xs text-gray-500">Recovery: {item.recovery_action || '—'}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 rounded-2xl bg-slate-50 p-4">
            <div className="text-sm font-semibold text-slate-700">Ostatnie logi</div>
            <div className="mt-3 space-y-2 text-xs text-slate-600">
              {logs.map((log) => (
                <div key={log.id} className="rounded-xl border bg-white px-3 py-2">
                  <span className="font-semibold">{log.category}</span>: {log.message}
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'
import { b2bApi } from '../api/config'

const currency = (value) => `${(value || 0).toLocaleString('pl-PL')} zł`

// ─── B2B Lead Score badge ───────────────────────────────────────────────────
function ScoreBadge({ score }) {
  const color =
    score >= 65 ? 'bg-green-100 text-green-800' :
    score >= 40 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-600'
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>{score}/100</span>
}

// ─── Offer modal ────────────────────────────────────────────────────────────
function OfferModal({ lead, onClose }) {
  if (!lead) return null
  const budget = lead.budget ? `${lead.budget.toLocaleString('pl-PL')} PLN` : 'do uzgodnienia'
  const fvat = lead.fvat_required ? 'Tak (faktura VAT)' : 'Nie wymagana'
  const template = `Dzień dobry,

Nawiązuję do Państwa zlecenia "${lead.title}" (${lead.source.toUpperCase()}).

Oferuję realizację zlecenia w ramach budżetu ${budget}.
Rozliczenie: ${fvat}

Moje kwalifikacje:
• Wieloletnie doświadczenie w branży
• Terminowa realizacja projektów
• Pełna dokumentacja i wsparcie po wdrożeniu

Proszę o kontakt w celu omówienia szczegółów.

Pozdrawiam,`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="font-semibold">✉️ Oferta handlowa</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl leading-none">✕</button>
        </div>
        <div className="p-4">
          <p className="text-xs text-gray-500 mb-2">Zlecenie: <span className="font-medium text-gray-800">{lead.title}</span></p>
          <textarea
            className="w-full h-56 border border-gray-300 rounded-lg p-3 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            defaultValue={template}
          />
        </div>
        <div className="flex gap-2 p-4 pt-0 justify-end">
          <button
            onClick={() => { navigator.clipboard.writeText(template); onClose() }}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700"
          >
            📋 Kopiuj ofertę
          </button>
          {lead.url && (
            <a
              href={lead.url}
              target="_blank"
              rel="noreferrer"
              className="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-700"
            >
              📥 Otwórz zlecenie
            </a>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── B2B Scanner Panel ───────────────────────────────────────────────────────
function B2BScannerPanel() {
  const [leads, setLeads] = useState([])
  const [total, setTotal] = useState(0)
  const [scannerEnabled, setScannerEnabled] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [offerLead, setOfferLead] = useState(null)
  const [filters, setFilters] = useState({ min_score: 0, fvat_only: false, min_budget: '' })
  const [loading, setLoading] = useState(false)

  const loadLeads = useCallback(async () => {
    setLoading(true)
    try {
      const params = { min_score: filters.min_score }
      if (filters.fvat_only) params.fvat_only = true
      if (filters.min_budget) params.min_budget = Number(filters.min_budget)
      const res = await b2bApi.getLeads(params)
      setLeads(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [filters])

  const loadStatus = async () => {
    try {
      const res = await b2bApi.getScannerStatus()
      setScannerEnabled(res.data.enabled)
      setScanning(res.data.running)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadLeads()
    loadStatus()
  }, [loadLeads])

  const handleToggleScanner = async () => {
    try {
      const res = await b2bApi.toggleScanner()
      setScannerEnabled(res.data.enabled)
    } catch {
      // ignore
    }
  }

  const handleScan = async () => {
    setScanning(true)
    try {
      await b2bApi.triggerScan()
      setTimeout(() => { loadLeads(); loadStatus() }, 3000)
    } catch {
      // ignore
    } finally {
      setTimeout(() => setScanning(false), 3000)
    }
  }

  return (
    <section className="rounded-2xl border bg-white p-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">🎯 Skaner B2B</h2>
          <p className="text-sm text-gray-500">Zlecenia z OLX, Useme, Oferteo — {total} leadów</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={handleToggleScanner}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
              scannerEnabled
                ? 'bg-red-100 text-red-700 hover:bg-red-200'
                : 'bg-green-100 text-green-700 hover:bg-green-200'
            }`}
          >
            {scannerEnabled ? '⏸️ Pauza Skanera' : '🚀 Uruchom Skaner B2B'}
          </button>
          <button
            onClick={handleScan}
            disabled={scanning}
            className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {scanning ? '⏳ Skanuję...' : '🔍 Skanuj teraz'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Min. LeadScore</label>
          <input
            type="number" min={0} max={100}
            className="w-24 border border-gray-300 rounded-lg px-2 py-1 text-sm"
            value={filters.min_score}
            onChange={(e) => setFilters(f => ({ ...f, min_score: Number(e.target.value) }))}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Min. Budżet (PLN)</label>
          <input
            type="number" min={0}
            className="w-28 border border-gray-300 rounded-lg px-2 py-1 text-sm"
            placeholder="dowolny"
            value={filters.min_budget}
            onChange={(e) => setFilters(f => ({ ...f, min_budget: e.target.value }))}
          />
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={filters.fvat_only}
            onChange={(e) => setFilters(f => ({ ...f, fvat_only: e.target.checked }))}
            className="accent-blue-600"
          />
          Tylko z Fakturą VAT
        </label>
        <button
          onClick={loadLeads}
          className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-200"
        >
          🔄 Odśwież
        </button>
      </div>

      {/* Lead list */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
        {loading && <div className="text-sm text-gray-400">Ładuję...</div>}
        {!loading && leads.length === 0 && (
          <div className="rounded-xl bg-gray-50 p-6 text-center text-sm text-gray-400">
            Brak leadów — kliknij "Skanuj teraz" aby pobrać zlecenia.
          </div>
        )}
        {leads.map((lead) => {
          const ci = lead.contact_info || {}
          const phones = ci.phones?.join(', ') || '—'
          const emails = ci.emails?.join(', ') || '—'
          return (
            <div key={lead.id} className="rounded-xl border p-4 text-sm hover:shadow-sm transition-shadow">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold truncate">{lead.title}</div>
                  <div className="text-xs text-gray-500 mt-1 space-x-2">
                    <span className="uppercase font-medium">{lead.source}</span>
                    {lead.budget && <span>· 💰 {lead.budget.toLocaleString('pl-PL')} PLN</span>}
                    {lead.fvat_required && <span className="text-green-600">· 🧾 FV TAK</span>}
                  </div>
                  {lead.description && (
                    <p className="mt-2 text-gray-600 text-xs line-clamp-2">{lead.description}</p>
                  )}
                  <div className="mt-1 text-xs text-gray-400">
                    📞 {phones} &nbsp; 📧 {emails}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <ScoreBadge score={lead.score} />
                  <div className="flex gap-1">
                    <button
                      onClick={() => setOfferLead(lead)}
                      className="bg-blue-600 text-white px-2 py-1 rounded-lg text-xs font-semibold hover:bg-blue-700"
                    >
                      ✉️ Generuj Ofertę
                    </button>
                    {lead.url && (
                      <a
                        href={lead.url}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-gray-100 text-gray-700 px-2 py-1 rounded-lg text-xs font-semibold hover:bg-gray-200"
                      >
                        📥
                      </a>
                    )}
                  </div>
                  {lead.sent_to_telegram && (
                    <span className="text-xs text-blue-500">✈️ Telegram</span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <OfferModal lead={offerLead} onClose={() => setOfferLead(null)} />
    </section>
  )
}


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

      {/* B2B Scanner Panel */}
      <B2BScannerPanel />
    </div>
  )
}

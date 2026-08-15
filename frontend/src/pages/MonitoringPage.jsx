import React, { useCallback, useEffect, useState } from 'react'
import api from '../api/api'

const LEVEL_STYLES = {
  info: 'bg-blue-100 text-blue-700',
  warning: 'bg-yellow-100 text-yellow-700',
  error: 'bg-red-100 text-red-700',
  critical: 'bg-purple-100 text-purple-700',
}

export default function MonitoringPage() {
  const [health, setHealth] = useState(null)
  const [errors, setErrors] = useState([])
  const [scaling, setScaling] = useState(null)
  const [stats, setStats] = useState({ info: 0, warning: 0, error: 0, critical: 0, total: 0 })
  const [form, setForm] = useState({ message: '', source: 'manual', level: 'error' })

  const load = useCallback(async () => {
    try {
      const [healthRes, errorsRes, scalingRes, statsRes] = await Promise.all([
        api.get('/monitoring/health'),
        api.get('/monitoring/errors'),
        api.get('/monitoring/scaling'),
        api.get('/monitoring/stats'),
      ])
      setHealth(healthRes.data)
      setErrors(errorsRes.data || [])
      setScaling(scalingRes.data)
      setStats(statsRes.data || { info: 0, warning: 0, error: 0, critical: 0, total: 0 })
    } catch { }
  }, [])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const interval = setInterval(load, 10000)
    return () => clearInterval(interval)
  }, [load])

  const submitError = async (e) => {
    e.preventDefault()
    try {
      await api.post('/monitoring/errors', form)
      setForm({ message: '', source: 'manual', level: 'error' })
      load()
    } catch { }
  }

  const restart = async () => {
    try {
      await api.post('/monitoring/restart-sim')
      load()
    } catch { }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">🖥️ Monitoring systemu</h1>
          <p className="text-sm text-gray-500 mt-1">Stan API, logi błędów, auto-skalowanie i symulacja restartu.</p>
        </div>
        <button onClick={restart} className="px-4 py-2 bg-yellow-600 text-white rounded-lg text-sm font-medium hover:bg-yellow-700">
          Symuluj restart
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-5 space-y-2">
          <div className="font-semibold">Health</div>
          <div className="text-sm text-gray-600">DB: <span className={health?.db_ok ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>{health?.db_ok ? 'OK' : 'Błąd'}</span></div>
          <div className="text-sm text-gray-600">Leady: {health?.leads_count ?? '—'}</div>
          <div className="text-sm text-gray-600">Kampanie: {health?.campaigns_count ?? '—'}</div>
          <div className="text-sm text-gray-600">Uptime: {health?.uptime ?? '—'} s</div>
          <div className="text-sm text-gray-600">RAM: {health?.memory_mb ?? 0} MB</div>
        </div>
        <div className="bg-white rounded-xl border p-5 space-y-2">
          <div className="font-semibold">Auto-skalowanie</div>
          <div className="text-sm text-gray-600">Workerzy: {scaling?.current_workers ?? '—'} / {scaling?.max_workers ?? '—'}</div>
          <div className="text-sm text-gray-600">Obciążenie: {scaling?.load_pct ?? '—'}%</div>
          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mt-3">
            <div className="h-3 bg-blue-600 rounded-full" style={{ width: `${Math.min(scaling?.load_pct || 0, 100)}%` }} />
          </div>
        </div>
        <div className="bg-white rounded-xl border p-5 space-y-2">
          <div className="font-semibold">Statystyki błędów</div>
          <div className="text-sm text-gray-600">Info: {stats.info}</div>
          <div className="text-sm text-gray-600">Warning: {stats.warning}</div>
          <div className="text-sm text-gray-600">Error: {stats.error}</div>
          <div className="text-sm text-gray-600">Critical: {stats.critical}</div>
        </div>
      </div>

      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Zaloguj błąd ręcznie</h2>
        <form onSubmit={submitError} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="text-xs text-gray-500 block mb-1">Komunikat</label>
            <input required className="border rounded px-3 py-2 text-sm w-full" value={form.message} onChange={e => setForm(f => ({ ...f, message: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Źródło</label>
            <input className="border rounded px-3 py-2 text-sm w-full" value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Poziom</label>
            <select className="border rounded px-3 py-2 text-sm w-full" value={form.level} onChange={e => setForm(f => ({ ...f, level: e.target.value }))}>
              {['info', 'warning', 'error', 'critical'].map(level => <option key={level} value={level}>{level}</option>)}
            </select>
          </div>
          <div className="md:col-span-4">
            <button type="submit" className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700">Dodaj wpis</button>
          </div>
        </form>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-6 py-4 border-b flex items-center justify-between">
          <div>
            <h2 className="font-semibold">Ostatnie błędy</h2>
            <p className="text-xs text-gray-400 mt-1">Auto-odświeżanie co 10 sekund</p>
          </div>
          <button onClick={load} className="px-3 py-1.5 bg-gray-100 rounded-lg text-sm hover:bg-gray-200">Odśwież</button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-4 py-3">Czas</th>
                <th className="text-left px-4 py-3">Poziom</th>
                <th className="text-left px-4 py-3">Źródło</th>
                <th className="text-left px-4 py-3">Komunikat</th>
              </tr>
            </thead>
            <tbody>
              {errors.map(item => (
                <tr key={item.id} className="border-t">
                  <td className="px-4 py-3">{item.created_at ? new Date(item.created_at).toLocaleString('pl-PL') : '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${LEVEL_STYLES[item.level] || 'bg-gray-100 text-gray-700'}`}>{item.level}</span>
                  </td>
                  <td className="px-4 py-3">{item.source || '—'}</td>
                  <td className="px-4 py-3">{item.message}</td>
                </tr>
              ))}
              {errors.length === 0 && (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-gray-400">Brak logów błędów.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

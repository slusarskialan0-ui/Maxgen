import React, { useEffect, useState, useCallback } from 'react'
import api, { API_BASE } from '../api/api'

export default function SyncPage() {
  const [backups, setBackups] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)

  const load = useCallback(async () => {
    try { const r = await api.get('/sync/backups'); setBackups(r.data) } catch { }
  }, [])

  useEffect(() => { load() }, [load])

  const doBackup = async () => {
    setLoading(true); setMessage(null)
    try {
      const r = await api.post('/sync/backup')
      setMessage({ type: 'success', text: `✅ Backup utworzony: ${r.data.filename} (${(r.data.size_bytes / 1024).toFixed(1)} KB)` })
      load()
    } catch (e) { setMessage({ type: 'error', text: `❌ Błąd: ${e.message}` }) }
    setLoading(false)
  }

  const doRecovery = async () => {
    if (!window.confirm('Uruchomić odtwarzanie z ostatniej kopii?')) return
    try {
      const r = await api.post('/sync/recovery')
      setMessage({ type: 'success', text: `✅ ${r.data.message} (z: ${r.data.recovered_from})` })
    } catch (e) { setMessage({ type: 'error', text: `❌ ${e?.response?.data?.detail || e.message}` }) }
  }

  const exportCsv = () => { window.open(`${API_BASE}/sync/export/leads/csv`, '_blank') }
  const exportJson = () => { window.open(`${API_BASE}/sync/export/leads/json`, '_blank') }

  const handleImport = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const r = await api.post('/sync/import/leads/json', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMessage({ type: 'success', text: `✅ Import zakończony: dodano ${r.data.added}, pominięto ${r.data.skipped}` })
    } catch (e) { setMessage({ type: 'error', text: `❌ Błąd importu: ${e?.response?.data?.detail || e.message}` }) }
    e.target.value = ''
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">🔄 Synchronizacja i Backup</h1>
        <p className="text-sm text-gray-500 mt-1">Eksport, import, auto-backup i odtwarzanie danych</p>
      </div>

      {message && (
        <div className={`rounded-xl p-4 text-sm ${message.type === 'success' ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-800'}`}>
          {message.text}
        </div>
      )}

      {/* Export */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">📤 Eksport danych</h2>
        <div className="flex flex-wrap gap-3">
          <button onClick={exportCsv} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
            ⬇ Eksport CSV
          </button>
          <button onClick={exportJson} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
            ⬇ Eksport JSON
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-3">Pobiera wszystkie leady w wybranym formacie</p>
      </div>

      {/* Import */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">📥 Import leadów (JSON)</h2>
        <label className="cursor-pointer inline-block px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700">
          📂 Wybierz plik JSON
          <input type="file" accept=".json" className="hidden" onChange={handleImport} />
        </label>
        <p className="text-xs text-gray-400 mt-3">Format: tablica obiektów z polami: full_name, email, phone, company, industry, voivodeship, stage, notes</p>
      </div>

      {/* Backup */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">💾 Backup bazy danych</h2>
        <div className="flex flex-wrap gap-3 mb-4">
          <button onClick={doBackup} disabled={loading} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">
            {loading ? 'Tworzę backup...' : '💾 Utwórz backup teraz'}
          </button>
          <button onClick={doRecovery} className="px-4 py-2 bg-yellow-600 text-white rounded-lg text-sm hover:bg-yellow-700">
            🔄 Odtwórz z ostatniego backup
          </button>
        </div>
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-600">Historia backupów</h3>
          {backups.length === 0 && <p className="text-sm text-gray-400">Brak backupów</p>}
          {backups.map(b => (
            <div key={b.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg text-sm">
              <div>
                <span className="font-medium text-gray-700">{b.filename}</span>
                <span className="text-gray-400 ml-2 text-xs">{(b.size_bytes / 1024).toFixed(1)} KB</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={`px-2 py-0.5 rounded-full text-xs ${b.status === 'ok' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>{b.status}</span>
                <span className="text-xs text-gray-400">{b.created_at ? new Date(b.created_at).toLocaleString('pl-PL') : ''}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

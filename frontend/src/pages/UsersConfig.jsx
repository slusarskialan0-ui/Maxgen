import React, { useEffect, useState, useCallback } from 'react'
import api from '../api/api'

export default function UsersConfig() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', display_name: '', role: 'agent', email: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { const r = await api.get('/users'); setUsers(r.data) } catch { }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    try { await api.post('/users', form); setShowForm(false); setForm({ username: '', display_name: '', role: 'agent', email: '' }); load() } catch { }
    setSaving(false)
  }

  const toggleActive = async (u) => {
    try { await api.patch(`/users/${u.id}`, { active: !u.active }); load() } catch { }
  }

  const del = async (id) => {
    if (!window.confirm('Usuń użytkownika?')) return
    try { await api.delete(`/users/${id}`); load() } catch { }
  }

  if (loading) return <div className="p-8 text-gray-400">Ładowanie...</div>

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">👤 Użytkownicy</h1>
          <p className="text-sm text-gray-500 mt-1">Agenci i menedżerowie do auto-przypisywania leadów</p>
        </div>
        <button onClick={() => setShowForm(v => !v)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
          + Nowy użytkownik
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">Nowy użytkownik</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[['username','Login *', true], ['display_name','Imię i nazwisko', false], ['email','E-mail', false]].map(([k, lbl, req]) => (
              <div key={k}>
                <label className="text-xs text-gray-500 block mb-1">{lbl}</label>
                <input required={req} className="border rounded px-3 py-2 text-sm w-full" value={form[k]} onChange={e => setForm(f => ({ ...f, [k]: e.target.value }))} />
              </div>
            ))}
            <div>
              <label className="text-xs text-gray-500 block mb-1">Rola</label>
              <select className="border rounded px-3 py-2 text-sm w-full" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                <option value="agent">Agent</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="md:col-span-2 flex gap-3">
              <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50">{saving ? 'Zapisuję...' : 'Utwórz'}</button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">Anuluj</button>
            </div>
          </form>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Login</th>
              <th className="px-4 py-3 text-left">Imię</th>
              <th className="px-4 py-3 text-left">Rola</th>
              <th className="px-4 py-3 text-left">E-mail</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Akcje</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map(u => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium">{u.username}</td>
                <td className="px-4 py-3 text-gray-600">{u.display_name || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${u.role === 'admin' ? 'bg-red-100 text-red-700' : u.role === 'manager' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>{u.role}</span>
                </td>
                <td className="px-4 py-3 text-gray-500">{u.email || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${u.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>{u.active ? 'Aktywny' : 'Nieaktywny'}</span>
                </td>
                <td className="px-4 py-3 flex gap-2">
                  <button onClick={() => toggleActive(u)} className="text-xs border rounded px-2 py-1 hover:bg-gray-50">{u.active ? 'Wyłącz' : 'Włącz'}</button>
                  <button onClick={() => del(u.id)} className="text-xs border border-red-200 text-red-600 rounded px-2 py-1 hover:bg-red-50">Usuń</button>
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">Brak użytkowników</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  )
}

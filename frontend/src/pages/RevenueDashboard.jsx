import React, { useEffect, useState } from 'react'
import api from '../api/api'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

export default function RevenueDashboard() {
  const [data, setData] = useState({ total_revenue: 0, by_month: [] })

  useEffect(() => {
    api.get('/analytics/revenue').then(r => setData(r.data)).catch(() => {})
  }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">💸 Dashboard przychodów</h1>
      <div className="rounded-xl border bg-emerald-50 p-6">
        <div className="text-sm text-emerald-700">Łączny przychód</div>
        <div className="text-4xl font-bold text-emerald-700">{(data.total_revenue || 0).toLocaleString('pl-PL')} zł</div>
      </div>
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Przychód miesięczny</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data.by_month || []}>
            <XAxis dataKey="month" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="revenue" fill="#10b981" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

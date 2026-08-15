import React, { useEffect, useState } from 'react'
import api from '../api/api'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'

export default function TrafficDashboard() {
  const [usage, setUsage] = useState({ api_requests_today: 0, api_requests_month: 0, points: [] })

  useEffect(() => {
    Promise.all([api.get('/biznes/usage'), api.get('/dev/analytics')])
      .then(([usageRes, analyticsRes]) => {
        const points = (analyticsRes.data?.top_endpoints || []).map((row) => ({
          endpoint: row.endpoint,
          count: row.count,
        }))
        setUsage({ ...usageRes.data, points })
      })
      .catch(() => {})
  }, [])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">📈 Dashboard ruchu</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="rounded-xl border bg-blue-50 p-5"><div className="text-3xl font-bold text-blue-700">{usage.api_requests_today}</div><div className="text-sm text-blue-700">Requesty dzisiaj</div></div>
        <div className="rounded-xl border bg-indigo-50 p-5"><div className="text-3xl font-bold text-indigo-700">{usage.api_requests_month}</div><div className="text-sm text-indigo-700">Requesty w miesiącu</div></div>
      </div>
      <div className="bg-white rounded-xl border p-6">
        <h2 className="font-semibold mb-4">Najczęściej używane endpointy</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={usage.points || []}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="endpoint" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#2563eb" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

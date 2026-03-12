import { useState, useEffect } from 'react'
import { fetchMetrics } from './api'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts'

const POLL_MS = 3000
const HISTORY_MAX = 30

export default function App() {
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const data = await fetchMetrics()
        if (cancelled) return
        setMetrics(data)
        setError(null)
        setHistory((prev) => {
          const next = [
            ...prev,
            {
              time: new Date().toLocaleTimeString(),
              total: data.totalRequests,
              status2xx: data.status2xx,
              status4xx: data.status4xx,
              status5xx: data.status5xx,
              rateLimited: data.rateLimited,
              latencyAvg: data.latencyAvgMs,
            },
          ]
          return next.slice(-HISTORY_MAX)
        })
      } catch (e) {
        if (!cancelled) setError(e.message)
      }
    }
    poll()
    const id = setInterval(poll, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  if (error) {
    return (
      <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
        <h1>API Gateway Dashboard</h1>
        <p style={{ color: 'crimson' }}>Error: {error}. Is the gateway running on port 8000?</p>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
        <h1>API Gateway Dashboard</h1>
        <p>Loading metrics…</p>
      </div>
    )
  }

  const statusData = [
    { name: '2xx', count: metrics.status2xx, fill: '#22c55e' },
    { name: '4xx', count: metrics.status4xx, fill: '#eab308' },
    { name: '5xx', count: metrics.status5xx, fill: '#ef4444' },
    { name: 'Rate limited', count: metrics.rateLimited, fill: '#64748b' },
  ]

  return (
    <div style={{ padding: 24, fontFamily: 'sans-serif', maxWidth: 1000 }}>
      <h1>API Gateway Dashboard</h1>
      <p style={{ color: '#64748b' }}>Refreshes every {POLL_MS / 1000}s</p>

      <section style={{ marginTop: 24 }}>
        <h2>Totals</h2>
        <p><strong>Total requests:</strong> {metrics.totalRequests}</p>
        <p><strong>2xx:</strong> {metrics.status2xx} · <strong>4xx:</strong> {metrics.status4xx} · <strong>5xx:</strong> {metrics.status5xx} · <strong>Rate limited:</strong> {metrics.rateLimited}</p>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Status breakdown</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={statusData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill={(props) => props.payload?.fill ?? '#8884d8'} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>Latency (ms)</h2>
        <p>Avg: <strong>{metrics.latencyAvgMs}</strong> · P50: {metrics.latencyP50Ms} · P95: {metrics.latencyP95Ms} · P99: {metrics.latencyP99Ms}</p>
      </section>

      {history.length > 0 && (
        <section style={{ marginTop: 24 }}>
          <h2>Request rate over time</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="total" name="Total" stroke="#3b82f6" dot={false} />
              <Line type="monotone" dataKey="status2xx" name="2xx" stroke="#22c55e" dot={false} />
              <Line type="monotone" dataKey="rateLimited" name="Rate limited" stroke="#64748b" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}
    </div>
  )
}

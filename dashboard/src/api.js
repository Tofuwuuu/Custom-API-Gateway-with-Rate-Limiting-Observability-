const GATEWAY_URL = import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8000'

export async function fetchMetrics() {
  const res = await fetch(`${GATEWAY_URL}/metrics`)
  if (!res.ok) throw new Error(`Metrics failed: ${res.status}`)
  return res.json()
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMetrics } from '../api/client'
import { useOrg } from '../org/OrgContext'

interface MetricLine {
  name: string
  labels: Record<string, string>
  value: number
  raw: string
}

function parsePrometheus(text: string): MetricLine[] {
  const lines = text.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#'))
  return lines.map((line) => {
    const match = line.match(/^(\S+?)(\{.*?\})?\s+(-?[\d.eE+]+)\s*$/)
    if (!match) return { name: line, labels: {}, value: NaN, raw: line }
    const name = match[1]
    const labelsStr = match[2] || ''
    const value = parseFloat(match[3])
    const labels: Record<string, string> = {}
    if (labelsStr) {
      const inner = labelsStr.slice(1, -1)
      inner.split(',').forEach((pair) => {
        const [k, v] = pair.split('=')
        if (k && v) labels[k.trim()] = v.trim().replace(/^"|"$/g, '')
      })
    }
    return { name, labels, value, raw: line }
  })
}

function formatValue(v: number): string {
  if (Number.isNaN(v)) return 'N/A'
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`
  if (v >= 1000) return `${(v / 1000).toFixed(1)}K`
  return v.toFixed(2)
}

export default function Metrics() {
  const { org } = useOrg()
  const orgId = org?.id
  const [filter, setFilter] = useState('')

  const { data: metricsText, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['metrics', orgId],
    queryFn: () => getMetrics(),
    enabled: !!orgId,
    refetchInterval: 30000,
  })

  const allMetrics = metricsText ? parsePrometheus(metricsText) : []
  const metricNames = [...new Set(allMetrics.map((m) => m.name))]
  const filtered = filter
    ? allMetrics.filter((m) => m.name.includes(filter.toLowerCase()))
    : allMetrics

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Metrics</h1>
          <p className="text-sm text-gray-400 mt-1">
            System and incident metrics (auto-refreshes every 30s)
          </p>
        </div>
        <button className="btn-secondary text-sm" onClick={() => refetch()}>
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="card p-8 flex items-center justify-center">
          <div className="animate-pulse text-gray-400">Loading metrics…</div>
        </div>
      )}

      {isError && (
        <div className="card p-6">
          <p className="text-sm text-red-400">
            Failed to load metrics: {(error as Error).message || 'Unknown error'}
          </p>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* Metric name filter */}
          <div className="flex items-center gap-3">
            <input
              className="input max-w-xs"
              placeholder="Filter metrics…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <span className="text-xs text-gray-500">
              {filtered.length} of {allMetrics.length} metrics
            </span>
          </div>

          {/* Metric groups */}
          {metricNames.map((name) => {
            const group = filtered.filter((m) => m.name === name)
            return (
              <div key={name} className="card p-6">
                <h2 className="text-sm font-semibold text-white mb-4 font-mono">{name}</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.map((m, i) => (
                    <div
                      key={i}
                      className="p-3 bg-surface-raised rounded-lg border border-gray-800"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-lg font-semibold text-white">
                          {formatValue(m.value)}
                        </span>
                        {Object.keys(m.labels).length > 0 && (
                          <div className="flex flex-wrap gap-1 justify-end">
                            {Object.entries(m.labels).map(([k, v]) => (
                              <span key={k} className="badge bg-gray-700/50 text-gray-400 text-xs">
                                {k}={v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}

          {allMetrics.length === 0 && (
            <div className="card p-8 text-center">
              <p className="text-sm text-gray-500">No metrics available.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}

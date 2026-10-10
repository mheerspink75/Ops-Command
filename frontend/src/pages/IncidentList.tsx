import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getIncidents } from '../api/client'
import { useOrg } from '../org/OrgContext'
import SeverityBadge from '../components/SeverityBadge'
import StatusBadge from '../components/StatusBadge'
import NewIncidentModal from '../components/NewIncidentModal'
import type { Incident, Page } from '../types'

const STATUSES = ['declared', 'investigating', 'identified', 'monitoring', 'resolved', 'closed']
const SEVERITIES = ['SEV1', 'SEV2', 'SEV3', 'SEV4']
const PAGE_SIZE = 20

export default function IncidentList() {
  const { org, loading: orgLoading } = useOrg()
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [severity, setSeverity] = useState('')
  const [offset, setOffset] = useState(0)
  const [showNew, setShowNew] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['incidents', org?.id, q, status, severity, offset],
    queryFn: () =>
      getIncidents(org!.id, {
        q: q || undefined,
        status: status || undefined,
        severity: severity || undefined,
        limit: PAGE_SIZE,
        offset,
      }),
    enabled: !!org,
  })

  if (orgLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
      </div>
    )
  }

  if (!org) {
    return (
      <div className="card text-center py-12">
        <p className="text-sm text-gray-400">No organization selected.</p>
      </div>
    )
  }

  const page = data as Page<Incident> | undefined
  const items = page?.items ?? []
  const total = page?.total ?? 0
  const hasMore = page?.has_more ?? false

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Incidents</h1>
          <p className="text-sm text-gray-400 mt-1">
            {total} total · {org.name}
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowNew(true)}>
          + Declare incident
        </button>
      </div>

      <div className="card flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[200px]">
          <label htmlFor="filter-q" className="label">
            Search
          </label>
          <input
            id="filter-q"
            className="input"
            placeholder="Search title or summary…"
            value={q}
            onChange={(e) => {
              setQ(e.target.value)
              setOffset(0)
            }}
          />
        </div>
        <div>
          <label htmlFor="filter-status" className="label">
            Status
          </label>
          <select
            id="filter-status"
            className="input !w-auto"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setOffset(0)
            }}
          >
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="filter-severity" className="label">
            Severity
          </label>
          <select
            id="filter-severity"
            className="input !w-auto"
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value)
              setOffset(0)
            }}
          >
            <option value="">All</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="card !p-0 overflow-hidden">
        {error ? (
          <div className="p-4 text-red-400" role="alert">
            Failed to load incidents.
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent" />
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-gray-400">No incidents match your filters.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-gray-400">
                <th className="px-4 py-3 font-medium">Title</th>
                <th className="px-4 py-3 font-medium">Severity</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Declared</th>
              </tr>
            </thead>
            <tbody>
              {items.map((i) => (
                <tr key={i.id} className="border-b border-gray-800/50 last:border-0">
                  <td className="px-4 py-3">
                    <Link
                      to={`/incidents/${i.id}`}
                      className="text-gray-100 hover:text-accent font-medium"
                    >
                      {i.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={i.severity} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={i.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 whitespace-nowrap">
                    {new Date(i.declared_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {hasMore && (
        <div className="flex justify-center">
          <button
            className="btn-secondary"
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={isLoading}
          >
            Load more
          </button>
        </div>
      )}

      {showNew && (
        <NewIncidentModal
          onClose={() => setShowNew(false)}
          onCreated={(id) => {
            setShowNew(false)
            window.location.href = `/incidents/${id}`
          }}
        />
      )}
    </div>
  )
}

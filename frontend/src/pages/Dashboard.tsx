import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getIncidents } from '../api/client'
import { useOrg } from '../org/OrgContext'
import SeverityBadge from '../components/SeverityBadge'
import StatusBadge from '../components/StatusBadge'
import type { Incident, Page } from '../types'

const ACTIVE_STATUSES = ['declared', 'investigating', 'identified', 'monitoring']

function StatCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="card">
      <div className="text-sm text-gray-400">{label}</div>
      <div className={`text-3xl font-bold mt-1 ${accent ?? 'text-white'}`}>{value}</div>
    </div>
  )
}

function IncidentRow({ incident }: { incident: Incident }) {
  return (
    <Link
      to={`/incidents/${incident.id}`}
      className="flex items-center justify-between gap-4 px-4 py-3 rounded-lg hover:bg-surface-overlay transition-colors"
    >
      <div className="min-w-0">
        <div className="font-medium text-gray-100 truncate">{incident.title}</div>
        <div className="text-xs text-gray-500 mt-0.5">
          Declared {new Date(incident.declared_at).toLocaleString()}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <SeverityBadge severity={incident.severity} />
        <StatusBadge status={incident.status} />
      </div>
    </Link>
  )
}

export default function Dashboard() {
  const { org, loading: orgLoading } = useOrg()

  const { data, isLoading, error } = useQuery({
    queryKey: ['incidents', org?.id, 'dashboard'],
    queryFn: () => getIncidents(org!.id, { limit: 100 }),
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
        <h2 className="text-lg font-semibold text-white">No organization</h2>
        <p className="text-sm text-gray-400 mt-2">
          You are not a member of any organization yet. Create one to get started.
        </p>
      </div>
    )
  }

  const incidents: Incident[] = (data as Page<Incident> | undefined)?.items ?? []
  const active = incidents.filter((i) => ACTIVE_STATUSES.includes(i.status))
  const sev1 = active.filter((i) => i.severity === 'SEV1').length
  const sev2 = active.filter((i) => i.severity === 'SEV2').length
  const resolved = incidents.filter((i) => i.status === 'resolved' || i.status === 'closed').length
  const recent = [...incidents].sort(
    (a, b) => new Date(b.declared_at).getTime() - new Date(a.declared_at).getTime(),
  ).slice(0, 5)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-gray-400 mt-1">{org.name}</p>
        </div>
        <Link to="/incidents" className="btn-primary">
          View all incidents
        </Link>
      </div>

      {error ? (
        <div className="card text-red-400" role="alert">
          Failed to load incidents. Please try again.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Active incidents" value={active.length} accent="text-accent" />
            <StatCard label="SEV1 active" value={sev1} accent="text-red-400" />
            <StatCard label="SEV2 active" value={sev2} accent="text-orange-400" />
            <StatCard label="Resolved / closed" value={resolved} accent="text-green-400" />
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-3">Active incidents</h2>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-accent" />
              </div>
            ) : active.length === 0 ? (
              <p className="text-sm text-gray-400 py-4">No active incidents. All clear. 🎉</p>
            ) : (
              <div className="space-y-1">
                {active.map((i) => (
                  <IncidentRow key={i.id} incident={i} />
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-3">Recent incidents</h2>
            {recent.length === 0 ? (
              <p className="text-sm text-gray-400 py-4">No incidents yet.</p>
            ) : (
              <div className="space-y-1">
                {recent.map((i) => (
                  <IncidentRow key={i.id} incident={i} />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

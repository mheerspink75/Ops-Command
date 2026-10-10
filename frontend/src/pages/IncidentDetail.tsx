import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getIncident, transitionStatus, getTimeline, addTimelineEvent,
  getRoles, assignRole, getActionItems, createActionItem, updateActionItem,
  getPlaybooks, runPlaybook, getPlaybookRun, getAudit, getReport,
} from '../api/client'
import { useOrg } from '../org/OrgContext'
import { useIncidentSocket } from '../realtime/useIncidentSocket'
import SeverityBadge from '../components/SeverityBadge'
import StatusBadge from '../components/StatusBadge'
import ConnectionIndicator from '../components/ConnectionIndicator'
import type { Incident, TimelineEvent, ActionItem, RoleAssignment, Playbook, PlaybookRun, AuditEvent } from '../types'

const STATUS_FLOW = ['declared', 'investigating', 'identified', 'monitoring', 'resolved', 'closed'] as const

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function IncidentDetail() {
  const { incidentId: id } = useParams<{ incidentId: string }>()
  const navigate = useNavigate()
  const { org } = useOrg()
  const orgId = org?.id
  const queryClient = useQueryClient()
  const incidentId = id!

  const [timelineText, setTimelineText] = useState('')
  const [roleUserId, setRoleUserId] = useState('')
  const [roleName, setRoleName] = useState('')
  const [actionTitle, setActionTitle] = useState('')
  const [actionAssignee, setActionAssignee] = useState('')
  const [selectedPlaybook, setSelectedPlaybook] = useState('')
  const [activeRunId, setActiveRunId] = useState<string | null>(null)

  const { data: incident, isLoading: loadingIncident } = useQuery<Incident>({
    queryKey: ['incident', orgId, incidentId],
    queryFn: () => getIncident(orgId!, incidentId),
    enabled: !!orgId && !!incidentId,
  })

  const { data: timeline, isLoading: loadingTimeline } = useQuery<TimelineEvent[]>({
    queryKey: ['timeline', orgId, incidentId],
    queryFn: () => getTimeline(orgId!, incidentId),
    enabled: !!orgId && !!incidentId,
  })

  const { data: roles, isLoading: loadingRoles } = useQuery<RoleAssignment[]>({
    queryKey: ['roles', orgId, incidentId],
    queryFn: () => getRoles(orgId!, incidentId),
    enabled: !!orgId && !!incidentId,
  })

  const { data: actionItems, isLoading: loadingActions } = useQuery<ActionItem[]>({
    queryKey: ['actions', orgId, incidentId],
    queryFn: () => getActionItems(orgId!, incidentId),
    enabled: !!orgId && !!incidentId,
  })

  const { data: playbooks } = useQuery<Playbook[]>({
    queryKey: ['playbooks', orgId],
    queryFn: () => getPlaybooks(orgId!),
    enabled: !!orgId,
  })

  const { data: audit, isLoading: loadingAudit } = useQuery<AuditEvent[]>({
    queryKey: ['audit', orgId, incidentId],
    queryFn: () => getAudit(orgId!, incidentId),
    enabled: !!orgId && !!incidentId,
  })

  const { data: playbookRun, isLoading: loadingRun } = useQuery<PlaybookRun>({
    queryKey: ['playbookRun', orgId, incidentId, activeRunId],
    queryFn: () => getPlaybookRun(orgId!, incidentId, activeRunId!),
    enabled: !!orgId && !!activeRunId,
    // Poll while the run is in flight; stop once it reaches a terminal state.
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'succeeded' || status === 'failed' ? false : 1000
    },
  })

  const { state: wsState } = useIncidentSocket({
    incidentId,
    enabled: !!orgId && !!incidentId,
    onEvent: useCallback(() => {
      queryClient.invalidateQueries({ queryKey: ['incident', orgId, incidentId] })
      queryClient.invalidateQueries({ queryKey: ['timeline', orgId, incidentId] })
      queryClient.invalidateQueries({ queryKey: ['actions', orgId, incidentId] })
      queryClient.invalidateQueries({ queryKey: ['playbookRun', orgId, incidentId] })
    }, [queryClient, orgId, incidentId]),
  })

  const transitionMutation = useMutation({
    mutationFn: (status: string) => transitionStatus(orgId!, incidentId, status, incident!.version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incident', orgId, incidentId] })
    },
  })

  const addTimelineMutation = useMutation({
    mutationFn: (text: string) => addTimelineEvent(orgId!, incidentId, { message: text }),
    onSuccess: () => {
      setTimelineText('')
      queryClient.invalidateQueries({ queryKey: ['timeline', orgId, incidentId] })
    },
  })

  const assignRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => assignRole(orgId!, incidentId, { user_id: userId, role }),
    onSuccess: () => {
      setRoleUserId('')
      setRoleName('')
      queryClient.invalidateQueries({ queryKey: ['roles', orgId, incidentId] })
    },
  })

  const createActionMutation = useMutation({
    mutationFn: ({ title, assignee }: { title: string; assignee: string }) => createActionItem(orgId!, incidentId, { title, assignee_id: assignee || undefined }),
    onSuccess: () => {
      setActionTitle('')
      setActionAssignee('')
      queryClient.invalidateQueries({ queryKey: ['actions', orgId, incidentId] })
    },
  })

  const updateActionMutation = useMutation({
    mutationFn: ({ itemId, done }: { itemId: string; done: boolean }) => updateActionItem(orgId!, incidentId, itemId, { status: done ? 'done' : 'open' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions', orgId, incidentId] })
    },
  })

  const runPlaybookMutation = useMutation({
    mutationFn: (playbookId: string) => runPlaybook(orgId!, playbookId, { incident_id: incidentId, idempotency_key: `${incidentId}-${playbookId}-${Date.now()}` }),
    onSuccess: (run) => {
      setActiveRunId(run.id)
    },
  })

  const fetchReport = async () => {
    const report = await getReport(orgId!, incidentId)
    const blob = new Blob([report.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `incident-${incidentId}-report.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loadingIncident) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-pulse text-gray-400">Loading incident…</div>
      </div>
    )
  }

  if (!incident) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-gray-400">Incident not found.</p>
        <button className="btn-secondary" onClick={() => navigate('/incidents')}>Back to incidents</button>
      </div>
    )
  }

  const currentIndex = STATUS_FLOW.indexOf(incident.status as typeof STATUS_FLOW[number])
  const nextStatus = currentIndex < STATUS_FLOW.length - 1 ? STATUS_FLOW[currentIndex + 1] : null
  const prevStatus = currentIndex > 0 ? STATUS_FLOW[currentIndex - 1] : null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-semibold text-white">{incident.title}</h1>
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
            </div>
            {incident.summary && (
              <p className="text-sm text-gray-400">
                {incident.summary}
              </p>
            )}
            <div className="flex items-center gap-4 text-xs text-gray-500">
              <span>Created {timeAgo(incident.created_at)}</span>
              <span>Updated {timeAgo(incident.updated_at)}</span>
              <span>Version {incident.version}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ConnectionIndicator state={wsState} />
            <button className="btn-secondary text-sm" onClick={fetchReport}>
              Export Report
            </button>
          </div>
        </div>

        {/* Status transitions */}
        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-gray-500 mr-2">Transition:</span>
          {prevStatus && (
            <button
              className="btn-secondary text-xs"
              onClick={() => transitionMutation.mutate(prevStatus)}
              disabled={transitionMutation.isPending}
            >
              ← {prevStatus}
            </button>
          )}
          {nextStatus && (
            <button
              className="btn-primary text-xs"
              onClick={() => transitionMutation.mutate(nextStatus)}
              disabled={transitionMutation.isPending}
            >
              {nextStatus} →
            </button>
          )}
          {transitionMutation.isError && (
            <span className="text-xs text-red-400">
              {(transitionMutation.error as Error).message || 'Transition failed'}
            </span>
          )}
        </div>

        {/* Affected services */}
        {incident.services && incident.services.length > 0 && (
          <div className="mt-4">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Affected Services</h3>
            <div className="flex flex-wrap gap-2">
              {incident.services.map((svc) => (
                <span key={svc.id} className="badge bg-blue-500/20 text-blue-400">{svc.name}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Timeline */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Timeline</h2>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {loadingTimeline ? (
              <div className="animate-pulse text-gray-400 text-sm">Loading…</div>
            ) : timeline && timeline.length > 0 ? (
              timeline.map((event) => (
                <div key={event.id} className="flex gap-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-sm text-gray-300">{event.message}</p>
                    <p className="text-xs text-gray-500">{timeAgo(event.created_at)}</p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No timeline events yet.</p>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <input
              className="input flex-1"
              placeholder="Add timeline event…"
              value={timelineText}
              onChange={(e) => setTimelineText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && timelineText.trim()) {
                  addTimelineMutation.mutate(timelineText.trim())
                }
              }}
            />
            <button
              className="btn-primary"
              onClick={() => timelineText.trim() && addTimelineMutation.mutate(timelineText.trim())}
              disabled={addTimelineMutation.isPending || !timelineText.trim()}
            >
              Add
            </button>
          </div>
        </div>

        {/* Roles */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Roles</h2>
          <div className="space-y-3 max-h-48 overflow-y-auto">
            {loadingRoles ? (
              <div className="animate-pulse text-gray-400 text-sm">Loading…</div>
            ) : roles && roles.length > 0 ? (
              roles.map((r) => (
                <div key={r.user_id} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{r.role}</span>
                  <span className="text-xs text-gray-500">{r.username || r.user_id}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500">No roles assigned.</p>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <input
              className="input flex-1"
              placeholder="User ID"
              value={roleUserId}
              onChange={(e) => setRoleUserId(e.target.value)}
            />
            <input
              className="input flex-1"
              placeholder="Role (e.g. IC)"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
            />
            <button
              className="btn-primary"
              onClick={() => {
                if (roleUserId.trim() && roleName.trim()) {
                  assignRoleMutation.mutate({ userId: roleUserId.trim(), role: roleName.trim() })
                }
              }}
              disabled={assignRoleMutation.isPending || !roleUserId.trim() || !roleName.trim()}
            >
              Assign
            </button>
          </div>
        </div>

        {/* Action Items */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Action Items</h2>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {loadingActions ? (
              <div className="animate-pulse text-gray-400 text-sm">Loading…</div>
            ) : actionItems && actionItems.length > 0 ? (
              actionItems.map((item) => {
                const done = item.status === 'done'
                return (
                  <div key={item.id} className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={done}
                      onChange={() => updateActionMutation.mutate({ itemId: item.id, done: !done })}
                      className="accent-blue-500"
                    />
                    <div className="flex-1">
                      <p className={`text-sm ${done ? 'text-gray-500 line-through' : 'text-gray-300'}`}>
                        {item.title}
                      </p>
                      {item.assignee_username && (
                        <p className="text-xs text-gray-500">{item.assignee_username}</p>
                      )}
                    </div>
                  </div>
                )
              })
            ) : (
              <p className="text-sm text-gray-500">No action items.</p>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <input
              className="input flex-1"
              placeholder="Action item title"
              value={actionTitle}
              onChange={(e) => setActionTitle(e.target.value)}
            />
            <input
              className="input w-32"
              placeholder="Assignee"
              value={actionAssignee}
              onChange={(e) => setActionAssignee(e.target.value)}
            />
            <button
              className="btn-primary"
              onClick={() => {
                if (actionTitle.trim()) {
                  createActionMutation.mutate({ title: actionTitle.trim(), assignee: actionAssignee.trim() })
                }
              }}
              disabled={createActionMutation.isPending || !actionTitle.trim()}
            >
              Add
            </button>
          </div>
        </div>

        {/* Playbooks */}
        <div className="card p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Playbooks</h2>
          <div className="space-y-3">
            <select
              className="input w-full"
              value={selectedPlaybook}
              onChange={(e) => setSelectedPlaybook(e.target.value)}
            >
              <option value="">Select a playbook…</option>
              {playbooks?.map((pb) => (
                <option key={pb.id} value={pb.id}>{pb.name}</option>
              ))}
            </select>
            <button
              className="btn-primary w-full"
              onClick={() => selectedPlaybook && runPlaybookMutation.mutate(selectedPlaybook)}
              disabled={!selectedPlaybook || runPlaybookMutation.isPending}
            >
              {runPlaybookMutation.isPending ? 'Running…' : 'Run Playbook'}
            </button>
            {runPlaybookMutation.isError && (
              <p className="text-xs text-red-400">
                {(runPlaybookMutation.error as Error).message || 'Playbook run failed'}
              </p>
            )}
          </div>

          {activeRunId && (
            <div className="mt-4 p-3 bg-surface-raised rounded-lg border border-gray-800">
              <h3 className="text-xs font-medium text-gray-400 mb-2">Run Status</h3>
              {loadingRun ? (
                <div className="animate-pulse text-gray-400 text-sm">Loading…</div>
              ) : playbookRun ? (
                <div className="space-y-1">
                  <p className="text-sm text-gray-300">Status: {playbookRun.status}</p>
                  {Array.isArray(playbookRun.progress) && playbookRun.progress.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {playbookRun.progress.map((step: any, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className={step.status === 'completed' ? 'text-green-400' : step.status === 'failed' ? 'text-red-400' : 'text-gray-500'}>
                            {step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : '○'}
                          </span>
                          <span className="text-gray-400">{step.name || step.type || `Step ${i + 1}`}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {/* Audit Log */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-white mb-4">Audit Log</h2>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {loadingAudit ? (
            <div className="animate-pulse text-gray-400 text-sm">Loading…</div>
          ) : audit && audit.length > 0 ? (
            audit.map((event) => (
              <div key={event.id} className="flex items-center justify-between text-sm">
                <div>
                  <span className="text-gray-300">{event.action}</span>
                  {event.actor_username && (
                    <span className="text-gray-500 ml-2">by {event.actor_username}</span>
                  )}
                </div>
                <span className="text-xs text-gray-500">{timeAgo(event.created_at)}</span>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500">No audit events.</p>
          )}
        </div>
      </div>
    </div>
  )
}

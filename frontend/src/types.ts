// Shared API response types, mirroring the backend Pydantic schemas.

export interface User {
  id: string
  email: string
  username: string
  active: boolean
  created_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
  created_at: string
}

export interface Service {
  id: string
  organization_id: string
  name: string
  description: string | null
  tier: string
  status: string
  owner_team: string | null
  created_at: string
  updated_at: string
}

export interface RoleAssignment {
  user_id: string
  role: string
  assigned_at: string
  username: string | null
}

export interface Incident {
  id: string
  organization_id: string
  title: string
  summary: string | null
  severity: string
  status: string
  commander_id: string | null
  created_by_id: string
  declared_at: string
  resolved_at: string | null
  version: number
  created_at: string
  updated_at: string
  services: Service[]
  role_assignments: RoleAssignment[]
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface TimelineEvent {
  id: string
  incident_id: string
  event_type: string
  message: string
  metadata: Record<string, unknown> | null
  actor_id: string | null
  created_at: string
  actor_username: string | null
}

export interface ActionItem {
  id: string
  incident_id: string
  title: string
  description: string | null
  assignee_id: string | null
  status: string
  due_at: string | null
  created_at: string
  updated_at: string
  assignee_username: string | null
}

export interface Playbook {
  id: string
  organization_id: string
  name: string
  description: string | null
  enabled: boolean
  steps: unknown[]
  created_at: string
  updated_at: string
}

export interface PlaybookRun {
  id: string
  incident_id: string
  playbook_id: string
  status: string
  idempotency_key: string
  started_at: string | null
  completed_at: string | null
  error_detail: string | null
  progress: unknown[]
  created_at: string
}

export interface AuditEvent {
  id: string
  organization_id: string
  actor_id: string | null
  action: string
  resource_type: string
  resource_id: string | null
  sanitized_detail: Record<string, unknown> | null
  request_id: string | null
  created_at: string
  actor_username: string | null
}

export interface Report {
  incident_id: string
  format: string
  generated_at: string
  content: string
}

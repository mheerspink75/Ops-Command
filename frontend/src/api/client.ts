const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

let accessToken: string | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
  if (token) {
    localStorage.setItem('oc_access_token', token)
  } else {
    localStorage.removeItem('oc_access_token')
  }
}

export function getAccessToken(): string | null {
  if (accessToken) return accessToken
  return localStorage.getItem('oc_access_token')
}

export function setRefreshToken(token: string | null) {
  if (token) {
    localStorage.setItem('oc_refresh_token', token)
  } else {
    localStorage.removeItem('oc_refresh_token')
  }
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('oc_refresh_token')
}

export function clearTokens() {
  setAccessToken(null)
  setRefreshToken(null)
}

async function refreshTokens(): Promise<boolean> {
  const refresh = getRefreshToken()
  if (!refresh) return false

  try {
    const resp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!resp.ok) return false
    const data: TokenPair = await resp.json()
    setAccessToken(data.access_token)
    setRefreshToken(data.refresh_token)
    return true
  } catch {
    return false
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  isRetry = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const token = getAccessToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (resp.status === 401 && !isRetry) {
    const isAuthEndpoint = path.startsWith('/api/v1/auth/')
    if (!isAuthEndpoint) {
      const refreshed = await refreshTokens()
      if (refreshed) {
        return request<T>(path, options, true)
      }
      clearTokens()
      window.location.href = '/login'
    }
    throw new ApiError(401, 'unauthorized', 'Session expired')
  }

  if (!resp.ok) {
    let body: any = null
    try {
      body = await resp.json()
    } catch {
      /* not json */
    }
    const error = body?.error
    throw new ApiError(
      resp.status,
      error?.code || 'unknown',
      error?.message || resp.statusText,
      error?.details,
    )
  }

  if (resp.status === 204) return undefined as T
  return resp.json()
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

export function login(email: string, password: string): Promise<TokenPair> {
  return api.post<TokenPair>('/api/v1/auth/login', { email, password })
}

export function logout(refreshToken: string): Promise<void> {
  return api.post<void>('/api/v1/auth/logout', { refresh_token: refreshToken })
}

export function getMe(): Promise<any> {
  return api.get<any>('/api/v1/auth/me')
}

export function getOrganizations(): Promise<any[]> {
  return api.get<any[]>('/api/v1/organizations')
}

export function getIncidents(
  orgId: string,
  params?: { status?: string; severity?: string; q?: string; limit?: number; offset?: number },
): Promise<any> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.severity) qs.set('severity', params.severity)
  if (params?.q) qs.set('q', params.q)
  if (params?.limit) qs.set('limit', String(params.limit))
  if (params?.offset) qs.set('offset', String(params.offset))
  const query = qs.toString()
  return api.get<any>(`/api/v1/organizations/${orgId}/incidents${query ? `?${query}` : ''}`)
}

export function getIncident(orgId: string, incidentId: string): Promise<any> {
  return api.get<any>(`/api/v1/organizations/${orgId}/incidents/${incidentId}`)
}

export function createIncident(
  orgId: string,
  data: { title: string; summary?: string; severity: string; service_ids?: string[] },
): Promise<any> {
  return api.post<any>(`/api/v1/organizations/${orgId}/incidents`, data)
}

export function transitionStatus(
  orgId: string,
  incidentId: string,
  status: string,
  expectedVersion: number,
): Promise<any> {
  return api.post<any>(
    `/api/v1/organizations/${orgId}/incidents/${incidentId}/status`,
    { status, expected_version: expectedVersion },
  )
}

export async function getTimeline(orgId: string, incidentId: string): Promise<any[]> {
  const page = await api.get<{ items: any[] }>(`/api/v1/organizations/${orgId}/incidents/${incidentId}/timeline`)
  return page.items
}

export function addTimelineEvent(
  orgId: string,
  incidentId: string,
  data: { message: string; event_type?: string },
): Promise<any> {
  return api.post<any>(
    `/api/v1/organizations/${orgId}/incidents/${incidentId}/timeline`,
    data,
  )
}

export function getRoles(orgId: string, incidentId: string): Promise<any[]> {
  return api.get<any[]>(`/api/v1/organizations/${orgId}/incidents/${incidentId}/roles`)
}

export function assignRole(
  orgId: string,
  incidentId: string,
  data: { user_id: string; role: string },
): Promise<any> {
  return api.post<any>(
    `/api/v1/organizations/${orgId}/incidents/${incidentId}/roles`,
    data,
  )
}

export function getActionItems(orgId: string, incidentId: string): Promise<any[]> {
  return api.get<any[]>(`/api/v1/organizations/${orgId}/incidents/${incidentId}/action-items`)
}

export function createActionItem(
  orgId: string,
  incidentId: string,
  data: { title: string; description?: string; status?: string; assignee_id?: string },
): Promise<any> {
  return api.post<any>(
    `/api/v1/organizations/${orgId}/incidents/${incidentId}/action-items`,
    data,
  )
}

export function updateActionItem(
  orgId: string,
  incidentId: string,
  itemId: string,
  data: { status?: string; title?: string; description?: string },
): Promise<any> {
  return api.patch<any>(
    `/api/v1/organizations/${orgId}/incidents/${incidentId}/action-items/${itemId}`,
    data,
  )
}

export function getServices(orgId: string): Promise<any[]> {
  return api.get<any[]>(`/api/v1/organizations/${orgId}/services`)
}

export function getPlaybooks(orgId: string): Promise<any[]> {
  return api.get<any[]>(`/api/v1/organizations/${orgId}/playbooks`)
}

export function runPlaybook(
  orgId: string,
  playbookId: string,
  data: { incident_id: string; idempotency_key: string },
): Promise<any> {
  return api.post<any>(
    `/api/v1/organizations/${orgId}/incidents/${data.incident_id}/playbook-runs`,
    { playbook_id: playbookId, idempotency_key: data.idempotency_key },
  )
}

export function getPlaybookRun(orgId: string, incidentId: string, runId: string): Promise<any> {
  return api.get<any>(`/api/v1/organizations/${orgId}/incidents/${incidentId}/playbook-runs/${runId}`)
}

export async function getAudit(orgId: string, incidentId: string): Promise<any[]> {
  const page = await api.get<{ items: any[] }>(`/api/v1/organizations/${orgId}/audit?resource_id=${incidentId}`)
  return page.items
}

export function getReport(orgId: string, incidentId: string): Promise<any> {
  return api.get<any>(`/api/v1/organizations/${orgId}/incidents/${incidentId}/report`)
}

export function getMetrics(): Promise<string> {
  return api.get<string>('/metrics')
}

export function getWSUrl(incidentId: string): string {
  const wsBase = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
  const token = getAccessToken() || ''
  return `${wsBase}/api/v1/ws/incidents/${incidentId}?token=${encodeURIComponent(token)}`
}

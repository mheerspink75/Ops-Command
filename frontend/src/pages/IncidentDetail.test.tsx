import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import IncidentDetail from './IncidentDetail'
import * as client from '../api/client'
import * as org from '../org/OrgContext'

vi.mock('../org/OrgContext', () => ({
  useOrg: vi.fn(),
}))

vi.mock('../api/client', () => ({
  getIncident: vi.fn(),
  transitionStatus: vi.fn(),
  getTimeline: vi.fn(),
  addTimelineEvent: vi.fn(),
  getRoles: vi.fn(),
  assignRole: vi.fn(),
  getActionItems: vi.fn(),
  createActionItem: vi.fn(),
  updateActionItem: vi.fn(),
  getPlaybooks: vi.fn(),
  runPlaybook: vi.fn(),
  getPlaybookRun: vi.fn(),
  getAudit: vi.fn(),
  getReport: vi.fn(),
  getWSUrl: vi.fn(() => 'ws://localhost:8000/api/v1/ws/incidents/inc1'),
}))

const mockUseOrg = vi.mocked(org.useOrg)
const mockOrg = { id: 'o1', name: 'Alpha', slug: 'alpha', created_at: '2024-01-01T00:00:00Z' }

const incident = {
  id: 'inc1',
  organization_id: 'o1',
  title: 'Checkout Down',
  summary: 'Payments are failing',
  severity: 'SEV1',
  status: 'declared',
  commander_id: 'u2',
  created_by_id: 'u1',
  declared_at: '2024-02-01T00:00:00Z',
  resolved_at: null,
  version: 3,
  created_at: '2024-02-01T00:00:00Z',
  updated_at: '2024-02-01T01:00:00Z',
  services: [{ id: 's1', name: 'Payments', tier: 'critical' }],
  role_assignments: [{ user_id: 'u2', role: 'commander', assigned_at: '2024-02-01T00:05:00Z', username: 'dana' }],
}

const timeline = [
  { id: 'e1', incident_id: 'inc1', event_type: 'update', message: 'Declared the incident', metadata: null, actor_id: 'u1', created_at: '2024-02-01T00:01:00Z', actor_username: 'sam' },
]

const actionItems = [
  { id: 'a1', incident_id: 'inc1', title: 'Roll back deploy', description: null, assignee_id: 'u2', status: 'open', due_at: null, created_at: '2024-02-01T00:10:00Z', updated_at: '2024-02-01T00:10:00Z', assignee_username: 'dana' },
]

const audit = [
  { id: 'au1', organization_id: 'o1', actor_id: 'u1', action: 'incident.create', resource_type: 'incident', resource_id: 'inc1', sanitized_detail: null, request_id: null, created_at: '2024-02-01T00:00:00Z', actor_username: 'sam' },
]

function renderDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/incidents/inc1']}>
        <Routes>
          <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

class MockWebSocket {
  url: string
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(url: string) {
    this.url = url
  }
  close() {}
}

describe('IncidentDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal('WebSocket', MockWebSocket)
    mockUseOrg.mockReturnValue({ org: mockOrg, orgs: [mockOrg], setOrgId: vi.fn(), loading: false })
    vi.mocked(client.getIncident).mockResolvedValue(incident)
    vi.mocked(client.getTimeline).mockResolvedValue(timeline)
    vi.mocked(client.getRoles).mockResolvedValue(incident.role_assignments)
    vi.mocked(client.getActionItems).mockResolvedValue(actionItems)
    vi.mocked(client.getPlaybooks).mockResolvedValue([])
    vi.mocked(client.getAudit).mockResolvedValue(audit)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the incident header with title, severity, and status', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('Checkout Down')).toBeInTheDocument())
    expect(screen.getByLabelText('Severity SEV1')).toBeInTheDocument()
    expect(screen.getByLabelText('Status: Declared')).toBeInTheDocument()
    expect(screen.getByText('Payments are failing')).toBeInTheDocument()
  })

  it('renders the affected service', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('Affected Services')).toBeInTheDocument())
    expect(screen.getByText('Payments')).toBeInTheDocument()
  })

  it('renders timeline events with their messages', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('Declared the incident')).toBeInTheDocument())
  })

  it('renders assigned roles with usernames', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('commander')).toBeInTheDocument())
    // "dana" also appears as the action-item assignee, so expect >= 1.
    expect(screen.getAllByText('dana').length).toBeGreaterThanOrEqual(1)
  })

  it('renders action items with assignee', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('Roll back deploy')).toBeInTheDocument())
  })

  it('renders the audit log with actor', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('incident.create')).toBeInTheDocument())
    expect(screen.getByText(/by sam/i)).toBeInTheDocument()
  })

  it('shows the next status transition button', async () => {
    renderDetail()
    await waitFor(() => expect(screen.getByText('Checkout Down')).toBeInTheDocument())
    // declared -> investigating
    expect(screen.getByText('investigating →')).toBeInTheDocument()
  })

  it('shows a not-found state when the incident is missing', async () => {
    vi.mocked(client.getIncident).mockRejectedValue(new Error('404'))
    renderDetail()
    await waitFor(() => expect(screen.getByText('Incident not found.')).toBeInTheDocument())
  })
})

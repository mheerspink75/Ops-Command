import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import IncidentList from './IncidentList'
import { renderWithProviders } from '../test/test-utils'
import * as client from '../api/client'
import * as org from '../org/OrgContext'

vi.mock('../org/OrgContext', () => ({
  useOrg: vi.fn(),
}))

vi.mock('../api/client', () => ({
  getIncidents: vi.fn(),
  getServices: vi.fn(),
  createIncident: vi.fn(),
  ApiError: class ApiError extends Error {},
}))

const mockUseOrg = vi.mocked(org.useOrg)
const mockOrg = { id: 'o1', name: 'Alpha', slug: 'alpha', created_at: '2024-01-01T00:00:00Z' }

const baseIncident = {
  organization_id: 'o1',
  summary: null,
  commander_id: null,
  created_by_id: 'u1',
  resolved_at: null,
  version: 1,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  services: [],
  role_assignments: [],
}

const incidents = [
  { ...baseIncident, id: 'i1', title: 'First Incident', severity: 'SEV1', status: 'declared', declared_at: '2024-02-01T00:00:00Z' },
  { ...baseIncident, id: 'i2', title: 'Second Incident', severity: 'SEV2', status: 'resolved', declared_at: '2024-02-02T00:00:00Z' },
]

describe('IncidentList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrg.mockReturnValue({ org: mockOrg, orgs: [mockOrg], setOrgId: vi.fn(), loading: false })
  })

  it('renders the incident table with rows', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: incidents,
      total: 2,
      limit: 20,
      offset: 0,
      has_more: false,
    })
    renderWithProviders(<IncidentList />)
    await waitFor(() => expect(screen.getByText('First Incident')).toBeInTheDocument())
    expect(screen.getByText('Second Incident')).toBeInTheDocument()
    expect(screen.getByText(/2 total/i)).toBeInTheDocument()
  })

  it('shows the empty state when no incidents match', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
      has_more: false,
    })
    renderWithProviders(<IncidentList />)
    await waitFor(() => expect(screen.getByText(/no incidents match/i)).toBeInTheDocument())
  })

  it('shows a load more button when there are more pages', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: incidents,
      total: 40,
      limit: 20,
      offset: 0,
      has_more: true,
    })
    renderWithProviders(<IncidentList />)
    await waitFor(() => expect(screen.getByText('Load more')).toBeInTheDocument())
  })

  it('opens the declare incident modal', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: incidents,
      total: 2,
      limit: 20,
      offset: 0,
      has_more: false,
    })
    renderWithProviders(<IncidentList />)
    await waitFor(() => expect(screen.getByText('First Incident')).toBeInTheDocument())
    await userEvent.click(screen.getByText('+ Declare incident'))
    await waitFor(() => expect(screen.getByRole('dialog', { name: /create new incident/i })).toBeInTheDocument())
  })
})

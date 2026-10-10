import { screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Dashboard from './Dashboard'
import { renderWithProviders } from '../test/test-utils'
import * as client from '../api/client'
import * as org from '../org/OrgContext'

vi.mock('../org/OrgContext', () => ({
  useOrg: vi.fn(),
}))

vi.mock('../api/client', () => ({
  getIncidents: vi.fn(),
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
  { ...baseIncident, id: 'i1', title: 'SEV1 Outage', severity: 'SEV1', status: 'declared', declared_at: '2024-02-01T00:00:00Z' },
  { ...baseIncident, id: 'i2', title: 'SEV2 Slow', severity: 'SEV2', status: 'monitoring', declared_at: '2024-02-02T00:00:00Z' },
  { ...baseIncident, id: 'i3', title: 'Resolved One', severity: 'SEV3', status: 'resolved', declared_at: '2024-02-03T00:00:00Z' },
]

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrg.mockReturnValue({ org: mockOrg, orgs: [mockOrg], setOrgId: vi.fn(), loading: false })
  })

  it('renders the org name and active incidents', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: incidents,
      total: 3,
      limit: 100,
      offset: 0,
      has_more: false,
    })
    renderWithProviders(<Dashboard />)
    // Active incidents also appear in the "Recent" section, so expect >= 1.
    await waitFor(() => expect(screen.getAllByText('SEV1 Outage').length).toBeGreaterThanOrEqual(1))
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    // "Active incidents" is both a stat-card label and a section header.
    expect(screen.getAllByText('Active incidents').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Recent incidents')).toBeInTheDocument()
    expect(screen.getAllByText('SEV2 Slow').length).toBeGreaterThanOrEqual(1)
  })

  it('shows the empty state when there are no active incidents', async () => {
    vi.mocked(client.getIncidents).mockResolvedValue({
      items: [{ ...baseIncident, id: 'i3', title: 'Resolved One', severity: 'SEV3', status: 'resolved', declared_at: '2024-02-03T00:00:00Z' }],
      total: 1,
      limit: 100,
      offset: 0,
      has_more: false,
    })
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText(/no active incidents/i)).toBeInTheDocument())
  })

  it('shows an error state when the request fails', async () => {
    vi.mocked(client.getIncidents).mockRejectedValue(new Error('boom'))
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
  })

  it('prompts to create an organization when none exist', async () => {
    mockUseOrg.mockReturnValue({ org: null, orgs: [], setOrgId: vi.fn(), loading: false })
    renderWithProviders(<Dashboard />)
    await waitFor(() => expect(screen.getByText(/no organization/i)).toBeInTheDocument())
  })
})

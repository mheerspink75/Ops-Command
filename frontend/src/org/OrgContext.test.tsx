import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OrgProvider, useOrg } from './OrgContext'
import * as client from '../api/client'

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: true }),
}))

vi.mock('../api/client', () => ({
  getOrganizations: vi.fn(),
}))

const orgs = [
  { id: 'o1', name: 'Alpha', slug: 'alpha', created_at: '2024-01-01T00:00:00Z' },
  { id: 'o2', name: 'Beta', slug: 'beta', created_at: '2024-01-02T00:00:00Z' },
]

function OrgDisplay() {
  const { orgs, org, setOrgId, loading } = useOrg()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="count">{orgs.length}</span>
      <span data-testid="current">{org ? org.name : 'none'}</span>
      <button onClick={() => setOrgId('o2')}>pick-beta</button>
    </div>
  )
}

function renderOrg() {
  return render(
    <OrgProvider>
      <OrgDisplay />
    </OrgProvider>,
  )
}

describe('OrgProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('loads organizations and defaults to the first one', async () => {
    vi.mocked(client.getOrganizations).mockResolvedValue(orgs)
    renderOrg()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(client.getOrganizations).toHaveBeenCalled()
    expect(screen.getByTestId('count')).toHaveTextContent('2')
    expect(screen.getByTestId('current')).toHaveTextContent('Alpha')
    expect(localStorage.getItem('oc_org_id')).toBe('o1')
  })

  it('keeps a previously selected org when it still exists', async () => {
    localStorage.setItem('oc_org_id', 'o2')
    vi.mocked(client.getOrganizations).mockResolvedValue(orgs)
    renderOrg()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('current')).toHaveTextContent('Beta')
  })

  it('falls back to the first org when the stored one is missing', async () => {
    localStorage.setItem('oc_org_id', 'o999')
    vi.mocked(client.getOrganizations).mockResolvedValue(orgs)
    renderOrg()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('current')).toHaveTextContent('Alpha')
    expect(localStorage.getItem('oc_org_id')).toBe('o1')
  })

  it('switches the active organization on demand', async () => {
    vi.mocked(client.getOrganizations).mockResolvedValue(orgs)
    renderOrg()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    await userEvent.click(screen.getByText('pick-beta'))
    expect(screen.getByTestId('current')).toHaveTextContent('Beta')
    expect(localStorage.getItem('oc_org_id')).toBe('o2')
  })

  it('shows no organization when the list is empty', async () => {
    vi.mocked(client.getOrganizations).mockResolvedValue([])
    renderOrg()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('count')).toHaveTextContent('0')
    expect(screen.getByTestId('current')).toHaveTextContent('none')
  })
})

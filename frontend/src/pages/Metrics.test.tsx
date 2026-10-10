import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Metrics from './Metrics'
import { renderWithProviders } from '../test/test-utils'
import * as client from '../api/client'
import * as org from '../org/OrgContext'

vi.mock('../org/OrgContext', () => ({
  useOrg: vi.fn(),
}))

vi.mock('../api/client', () => ({
  getMetrics: vi.fn(),
}))

const mockUseOrg = vi.mocked(org.useOrg)
const mockOrg = { id: 'o1', name: 'Alpha', slug: 'alpha', created_at: '2024-01-01T00:00:00Z' }

const promText = [
  '# HELP http_requests_total Total HTTP requests',
  '# TYPE http_requests_total counter',
  'http_requests_total{method="GET",code="200"} 1027',
  'http_requests_total{method="POST",code="500"} 42',
  'process_cpu_seconds_total 1234.5',
].join('\n')

describe('Metrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseOrg.mockReturnValue({ org: mockOrg, orgs: [mockOrg], setOrgId: vi.fn(), loading: false })
  })

  it('parses and renders metric groups with values', async () => {
    vi.mocked(client.getMetrics).mockResolvedValue(promText)
    renderWithProviders(<Metrics />)
    await waitFor(() => expect(screen.getByText('http_requests_total')).toBeInTheDocument())
    // 1027 -> "1.0K", 42 -> "42.00", 1234.5 -> "1.2K"
    expect(screen.getByText('1.0K')).toBeInTheDocument()
    expect(screen.getByText('42.00')).toBeInTheDocument()
    expect(screen.getByText('1.2K')).toBeInTheDocument()
  })

  it('shows labels for labeled metrics', async () => {
    vi.mocked(client.getMetrics).mockResolvedValue(promText)
    renderWithProviders(<Metrics />)
    await waitFor(() => expect(screen.getByText('method=GET')).toBeInTheDocument())
    expect(screen.getByText('code=200')).toBeInTheDocument()
  })

  it('filters metric values by name', async () => {
    vi.mocked(client.getMetrics).mockResolvedValue(promText)
    renderWithProviders(<Metrics />)
    await waitFor(() => expect(screen.getByText('1.0K')).toBeInTheDocument())
    const filter = screen.getByPlaceholderText(/filter metrics/i)
    await userEvent.type(filter, 'cpu')
    // http_requests_total values are filtered out; cpu value remains.
    await waitFor(() => expect(screen.queryByText('1.0K')).not.toBeInTheDocument())
    expect(screen.getByText('1.2K')).toBeInTheDocument()
  })

  it('shows an error state when the request fails', async () => {
    vi.mocked(client.getMetrics).mockRejectedValue(new Error('boom'))
    renderWithProviders(<Metrics />)
    await waitFor(() => expect(screen.getByText(/failed to load metrics/i)).toBeInTheDocument())
  })
})

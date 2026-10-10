import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  const cases: [string, string][] = [
    ['declared', 'Declared'],
    ['investigating', 'Investigating'],
    ['identified', 'Identified'],
    ['monitoring', 'Monitoring'],
    ['resolved', 'Resolved'],
    ['closed', 'Closed'],
  ]

  it.each(cases)('renders %s as "%s"', (status, label) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByLabelText(`Status: ${label}`)).toBeInTheDocument()
  })

  it('falls back to the raw value for unknown statuses', () => {
    render(<StatusBadge status="weird" />)
    expect(screen.getByLabelText('Status: weird')).toBeInTheDocument()
  })
})

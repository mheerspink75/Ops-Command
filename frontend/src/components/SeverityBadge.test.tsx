import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import SeverityBadge from './SeverityBadge'

describe('SeverityBadge', () => {
  it('renders each known severity label', () => {
    for (const sev of ['SEV1', 'SEV2', 'SEV3', 'SEV4']) {
      const { unmount } = render(<SeverityBadge severity={sev} />)
      expect(screen.getByLabelText(`Severity ${sev}`)).toBeInTheDocument()
      unmount()
    }
  })

  it('falls back to the raw value for unknown severities', () => {
    render(<SeverityBadge severity="SEV9" />)
    expect(screen.getByLabelText('Severity SEV9')).toBeInTheDocument()
  })
})

import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import ConnectionIndicator from './ConnectionIndicator'

describe('ConnectionIndicator', () => {
  it('renders the connected state', () => {
    render(<ConnectionIndicator state="connected" />)
    expect(screen.getByLabelText('Connection: Live')).toBeInTheDocument()
  })

  it('renders the reconnecting state', () => {
    render(<ConnectionIndicator state="reconnecting" />)
    expect(screen.getByLabelText('Connection: Reconnecting…')).toBeInTheDocument()
  })

  it('renders the disconnected state', () => {
    render(<ConnectionIndicator state="disconnected" />)
    expect(screen.getByLabelText('Connection: Disconnected')).toBeInTheDocument()
  })
})

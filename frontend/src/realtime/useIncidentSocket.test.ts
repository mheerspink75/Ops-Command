import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useIncidentSocket } from './useIncidentSocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  close() {
    this.readyState = 3
    this.onclose?.()
  }

  // Test helpers
  open() {
    this.readyState = 1
    this.onopen?.()
  }
  sendEvent(payload: unknown) {
    this.onmessage?.({ data: JSON.stringify(payload) })
  }
}

describe('useIncidentSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('connects and reports the connected state', () => {
    const { result } = renderHook(() => useIncidentSocket({ incidentId: 'inc1' }))
    expect(result.current.state).toBe('disconnected')
    const ws = MockWebSocket.instances[0]
    expect(ws.url).toContain('/api/v1/ws/incidents/inc1')
    act(() => ws.open())
    expect(result.current.state).toBe('connected')
  })

  it('delivers non-ping events to the onEvent callback', () => {
    const onEvent = vi.fn()
    renderHook(() => useIncidentSocket({ incidentId: 'inc1', onEvent }))
    const ws = MockWebSocket.instances[0]
    act(() => ws.open())
    act(() => ws.sendEvent({ type: 'timeline_event', id: 'e1' }))
    expect(onEvent).toHaveBeenCalledWith({ type: 'timeline_event', id: 'e1' })
  })

  it('ignores ping heartbeats', () => {
    const onEvent = vi.fn()
    renderHook(() => useIncidentSocket({ incidentId: 'inc1', onEvent }))
    const ws = MockWebSocket.instances[0]
    act(() => ws.open())
    act(() => ws.sendEvent({ type: 'ping' }))
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('does not connect when disabled', () => {
    renderHook(() => useIncidentSocket({ incidentId: 'inc1', enabled: false }))
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('reconnects with backoff after a close', () => {
    vi.useFakeTimers()
    try {
      const { result } = renderHook(() => useIncidentSocket({ incidentId: 'inc1' }))
      const first = MockWebSocket.instances[0]
      act(() => first.open())
      expect(result.current.state).toBe('connected')
      act(() => first.close())
      expect(result.current.state).toBe('reconnecting')
      // Advance past the first backoff delay (1s).
      act(() => {
        vi.advanceTimersByTime(1100)
      })
      expect(MockWebSocket.instances).toHaveLength(2)
    } finally {
      vi.useRealTimers()
    }
  })
})

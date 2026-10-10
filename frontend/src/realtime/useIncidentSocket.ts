import { useEffect, useRef, useState, useCallback } from 'react'
import { getWSUrl } from '../api/client'

export type ConnectionState = 'connected' | 'disconnected' | 'reconnecting'

interface UseIncidentSocketOptions {
  incidentId: string
  onEvent?: (event: any) => void
  enabled?: boolean
}

export function useIncidentSocket({ incidentId, onEvent, enabled = true }: UseIncidentSocketOptions) {
  const [state, setState] = useState<ConnectionState>('disconnected')
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const connect = useCallback(() => {
    if (!enabled || !incidentId) return

    const url = getWSUrl(incidentId)
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setState('connected')
      reconnectAttempts.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type !== 'ping') {
          onEventRef.current?.(data)
        }
      } catch {
        /* ignore parse errors */
      }
    }

    ws.onclose = () => {
      setState('disconnected')
      if (enabled) {
        setState('reconnecting')
        const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000)
        reconnectAttempts.current += 1
        reconnectTimer.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [incidentId, enabled])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  return { state, reconnect: connect }
}

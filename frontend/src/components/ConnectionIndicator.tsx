import { ConnectionState } from '../realtime/useIncidentSocket'

const CONFIG: Record<ConnectionState, { color: string; label: string; dot: string }> = {
  connected: { color: 'text-green-400', label: 'Live', dot: 'bg-green-400' },
  reconnecting: { color: 'text-yellow-400', label: 'Reconnecting…', dot: 'bg-yellow-400 animate-pulse' },
  disconnected: { color: 'text-red-400', label: 'Disconnected', dot: 'bg-red-400' },
}

export default function ConnectionIndicator({ state }: { state: ConnectionState }) {
  const config = CONFIG[state]
  return (
    <div
      className={`flex items-center gap-2 text-sm ${config.color}`}
      role="status"
      aria-live="polite"
      aria-label={`Connection: ${config.label}`}
    >
      <span className={`w-2 h-2 rounded-full ${config.dot}`} aria-hidden="true" />
      <span>{config.label}</span>
    </div>
  )
}

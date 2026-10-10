const SEVERITY_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  SEV1: { label: 'SEV1', color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: '⬤' },
  SEV2: { label: 'SEV2', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', icon: '⬤' },
  SEV3: { label: 'SEV3', color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', icon: '⬤' },
  SEV4: { label: 'SEV4', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: '⬤' },
}

export default function SeverityBadge({ severity }: { severity: string }) {
  const config = SEVERITY_CONFIG[severity] || { label: severity, color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: '⬤' }
  return (
    <span
      className={`badge border ${config.color}`}
      role="status"
      aria-label={`Severity ${config.label}`}
    >
      <span aria-hidden="true">{config.icon}</span>
      <span className="ml-1">{config.label}</span>
    </span>
  )
}

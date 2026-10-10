const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  declared: { label: 'Declared', color: 'bg-red-500/20 text-red-400' },
  investigating: { label: 'Investigating', color: 'bg-orange-500/20 text-orange-400' },
  identified: { label: 'Identified', color: 'bg-yellow-500/20 text-yellow-400' },
  monitoring: { label: 'Monitoring', color: 'bg-blue-500/20 text-blue-400' },
  resolved: { label: 'Resolved', color: 'bg-green-500/20 text-green-400' },
  closed: { label: 'Closed', color: 'bg-gray-500/20 text-gray-400' },
}

export default function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || { label: status, color: 'bg-gray-500/20 text-gray-400' }
  return (
    <span className={`badge ${config.color}`} role="status" aria-label={`Status: ${config.label}`}>
      {config.label}
    </span>
  )
}

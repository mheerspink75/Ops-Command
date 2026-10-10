import { useState, FormEvent } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createIncident, getServices } from '../api/client'
import { useOrg } from '../org/OrgContext'
import { ApiError } from '../api/client'
import type { Service } from '../types'

const SEVERITIES = ['SEV1', 'SEV2', 'SEV3', 'SEV4']

interface Props {
  onClose: () => void
  onCreated: (id: string) => void
}

export default function NewIncidentModal({ onClose, onCreated }: Props) {
  const { org } = useOrg()
  const queryClient = useQueryClient()

  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [severity, setSeverity] = useState('SEV3')
  const [selectedServices, setSelectedServices] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  const { data: services } = useQuery({
    queryKey: ['services', org?.id],
    queryFn: () => getServices(org!.id),
    enabled: !!org,
  })

  const mutation = useMutation({
    mutationFn: () =>
      createIncident(org!.id, {
        title,
        summary: summary || undefined,
        severity,
        service_ids: selectedServices,
      }),
    onSuccess: (incident) => {
      queryClient.invalidateQueries({ queryKey: ['incidents', org?.id] })
      onCreated(incident.id)
    },
    onError: (err) => {
      if (err instanceof ApiError) setError(err.message)
      else setError('Failed to create incident.')
    },
  })

  const toggleService = (id: string) => {
    setSelectedServices((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id],
    )
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    mutation.mutate()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      role="dialog"
      aria-modal="true"
      aria-label="Create new incident"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="card w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Declare incident</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-xl leading-none"
            aria-label="Close dialog"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="ni-title" className="label">
              Title
            </label>
            <input
              id="ni-title"
              className="input"
              required
              minLength={3}
              maxLength={300}
              placeholder="e.g. Checkout latency spike"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="ni-summary" className="label">
              Summary <span className="text-gray-500">(optional)</span>
            </label>
            <textarea
              id="ni-summary"
              className="input min-h-[80px]"
              maxLength={5000}
              placeholder="What is happening?"
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="ni-severity" className="label">
              Severity
            </label>
            <select
              id="ni-severity"
              className="input"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="label">Affected services</span>
            {((services as Service[] | undefined) ?? []).length === 0 ? (
              <p className="text-sm text-gray-500">No services in this organization.</p>
            ) : (
              <div className="space-y-1 max-h-40 overflow-auto">
                {(services as Service[]).map((s) => (
                  <label
                    key={s.id}
                    className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedServices.includes(s.id)}
                      onChange={() => toggleService(s.id)}
                    />
                    {s.name}
                    <span className="text-xs text-gray-500">({s.tier})</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div role="alert" className="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={mutation.isPending}>
              {mutation.isPending ? 'Declaring…' : 'Declare incident'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

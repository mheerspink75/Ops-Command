import { useOrg } from '../org/OrgContext'

export default function OrgSelector() {
  const { orgs, org, setOrgId } = useOrg()

  if (orgs.length === 0) return null

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="org-select" className="text-sm text-gray-400">
        Organization
      </label>
      <select
        id="org-select"
        className="input !w-auto !py-1.5 text-sm"
        value={org?.id ?? ''}
        onChange={(e) => setOrgId(e.target.value)}
        aria-label="Select organization"
      >
        {orgs.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
          </option>
        ))}
      </select>
    </div>
  )
}

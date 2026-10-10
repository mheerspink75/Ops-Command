/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { getOrganizations } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Organization } from '../types'

interface OrgContextValue {
  orgs: Organization[]
  org: Organization | null
  setOrgId: (id: string) => void
  loading: boolean
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined)

const ORG_KEY = 'oc_org_id'

export function OrgProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [orgId, setOrgIdState] = useState<string | null>(() => localStorage.getItem(ORG_KEY))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isAuthenticated) {
      setOrgs([])
      setOrgIdState(null)
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    getOrganizations()
      .then((data) => {
        if (cancelled) return
        setOrgs(data)
        const current = localStorage.getItem(ORG_KEY)
        if (!current || !data.some((o) => o.id === current)) {
          const first = data[0]?.id ?? null
          if (first) {
            localStorage.setItem(ORG_KEY, first)
            setOrgIdState(first)
          } else {
            localStorage.removeItem(ORG_KEY)
            setOrgIdState(null)
          }
        }
      })
      .catch(() => {
        if (!cancelled) setOrgs([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  const setOrgId = useCallback((id: string) => {
    localStorage.setItem(ORG_KEY, id)
    setOrgIdState(id)
  }, [])

  const org = orgs.find((o) => o.id === orgId) ?? orgs[0] ?? null

  return (
    <OrgContext.Provider value={{ orgs, org, setOrgId, loading }}>
      {children}
    </OrgContext.Provider>
  )
}

export function useOrg() {
  const ctx = useContext(OrgContext)
  if (!ctx) throw new Error('useOrg must be used within OrgProvider')
  return ctx
}

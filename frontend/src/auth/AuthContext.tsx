/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react'
import { login as apiLogin, logout as apiLogout, getMe, clearTokens, setAccessToken, setRefreshToken, getRefreshToken } from '../api/client'

interface User {
  id: string
  email: string
  username: string
  active: boolean
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('oc_access_token')
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        clearTokens()
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiLogin(email, password)
    setAccessToken(data.access_token)
    setRefreshToken(data.refresh_token)
    const u = await getMe()
    setUser(u)
  }, [])

  const logout = useCallback(async () => {
    const refresh = getRefreshToken()
    if (refresh) {
      try {
        await apiLogout(refresh)
      } catch {
        /* ignore */
      }
    }
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

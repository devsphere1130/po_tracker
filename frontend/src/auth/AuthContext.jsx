import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    authApi.getCsrf().catch(() => {})
    authApi.me().then(setUser).catch(() => setUser(null)).finally(() => setReady(true))
    const expired = () => setUser(null)
    window.addEventListener('auth:expired', expired)
    return () => window.removeEventListener('auth:expired', expired)
  }, [])

  const login = useCallback(async (u, p) => {
    await authApi.getCsrf()
    setUser(await authApi.login(u, p))
  }, [])
  const logout = useCallback(async () => {
    try { await authApi.logout() } finally { setUser(null) }
  }, [])

  const value = useMemo(() => ({ user, ready, login, logout, isAdmin: user?.role === 'admin' }), [user, ready, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

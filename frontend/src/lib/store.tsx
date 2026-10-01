import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api } from './api'
import type { J } from '../types'

interface AppCtx {
  theme: 'light' | 'dark'
  setTheme: (t: 'light' | 'dark') => void
  health: J
  error: string | null
  setError: (e: string | null) => void
  version: number
  refresh: () => void
  bump: () => void
}

const C = createContext<AppCtx>(null as unknown as AppCtx)
export const useApp = () => useContext(C)

export function AppProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<'light' | 'dark'>(
    () => (document.documentElement.getAttribute('data-theme') as 'light' | 'dark') || 'light',
  )
  const [health, setHealth] = useState<J>(null)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState(0)

  const setTheme = (t: 'light' | 'dark') => {
    setThemeState(t)
    document.documentElement.setAttribute('data-theme', t)
    try { localStorage.setItem('vivad-theme', t) } catch { /* storage unavailable */ }
  }

  const refresh = useCallback(() => {
    setError(null)
    api.get('/health').then(setHealth).catch((e) => setHealth({ error: (e as Error).message }))
  }, [])
  const bump = useCallback(() => setVersion((v) => v + 1), [])

  useEffect(() => { refresh() }, [refresh])

  const value = useMemo(
    () => ({ theme, setTheme, health, error, setError, version, refresh, bump }),
    [theme, health, error, version, refresh, bump],
  )
  return <C.Provider value={value}>{children}</C.Provider>
}

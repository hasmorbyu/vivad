import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../lib/store'
import { useAuth } from '../lib/auth'
import { api, fmt } from '../lib/api'
import { useMediaQuery } from '../lib/useMediaQuery'
import { StatusChip } from './ui'

// Strictly five destinations. The last three require an open case.
const TABS = [
  { key: 'cases', label: 'Cases', icon: '▤', path: '/cases', needsCase: false },
  { key: 'new', label: 'New Case', icon: '＋', path: '/cases/new', needsCase: false },
  { key: 'investigation', label: 'Investigation', icon: '◈', path: '', needsCase: true, sub: '' },
  { key: 'graph', label: 'Graph', icon: '◎', path: 'graph', needsCase: true, sub: 'graph' },
  { key: 'review', label: 'Review', icon: '⚖', path: 'review', needsCase: true, sub: 'review' },
]

function currentCaseId(pathname: string): string | null {
  const m = pathname.match(/^\/cases\/([^/]+)/)
  if (!m || m[1] === 'new') return null
  return m[1]
}

export function TopBar() {
  const { theme, setTheme } = useApp()
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-line px-3 py-2">
      <NavLink to="/cases" className="tracking-[.18em]" style={{ fontWeight: 700, textDecoration: 'none', color: 'inherit' }}>VIVAD</NavLink>
      <span className="lbl hidden md:inline">ASSISTED DISPUTE-RESOLUTION</span>
      <form className="flex-1 min-w-[140px] max-w-[420px] ml-auto" onSubmit={(e) => { e.preventDefault(); if (q.trim().length >= 2) nav(`/search?q=${encodeURIComponent(q.trim())}`) }}>
        <input className="w-full" placeholder="SEARCH CASES · PARTIES · EVIDENCE · CLAIMS" aria-label="global search" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>
      <NotificationBell />
      <div className="flex gap-1" role="group" aria-label="theme">
        <button className={'btn ' + (theme === 'light' ? 'on' : '')} onClick={() => setTheme('light')} aria-pressed={theme === 'light'}>[ LIGHT ]</button>
        <button className={'btn ' + (theme === 'dark' ? 'on' : '')} onClick={() => setTheme('dark')} aria-pressed={theme === 'dark'}>[ DARK ]</button>
      </div>
      {user && (
        <div className="flex items-center gap-2">
          <span className="lbl hidden lg:inline">{user.name} · {fmt.label(user.role)}</span>
          <button className="btn" onClick={async () => { await logout(); nav('/login') }}>[ SIGN OUT ]</button>
        </div>
      )}
    </header>
  )
}

function NotificationBell() {
  const [unread, setUnread] = useState(0)
  useEffect(() => {
    const load = () => api.get('/notifications').then((d) => setUnread(d.unread)).catch(() => undefined)
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])
  return <NavLink className="btn no-underline" to="/notifications">[ ALERTS{unread ? ` · ${unread}` : ''} ]</NavLink>
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const loc = useLocation()
  const caseId = currentCaseId(loc.pathname)

  const to = (t: typeof TABS[number]) => {
    if (!t.needsCase) return t.path
    if (!caseId) return null
    return t.sub ? `/cases/${caseId}/${t.sub}` : `/cases/${caseId}`
  }
  const isActive = (t: typeof TABS[number]) => {
    const p = loc.pathname
    if (t.key === 'cases') return p === '/cases'
    if (t.key === 'new') return p === '/cases/new'
    if (t.key === 'graph') return caseId != null && /^\/cases\/[^/]+\/graph/.test(p)
    if (t.key === 'review') return caseId != null && /^\/cases\/[^/]+\/(review|hearings|decision|audit|report)/.test(p)
    return caseId != null && (p === `/cases/${caseId}` || /^\/cases\/[^/]+\/(parties|statements|evidence|timeline|claims|contradictions|legal)/.test(p))
  }

  return (
    <nav className="border-r border-line p-2 hidden lg:flex flex-col overflow-y-auto" aria-label="primary">
      <button className="btn btn-quiet w-full mb-2" onClick={onToggle} aria-label={collapsed ? 'expand navigation' : 'collapse navigation'} title={collapsed ? 'Expand' : 'Collapse'}>
        {collapsed ? '»' : '«'}
      </button>
      {TABS.map((t) => {
        const href = to(t)
        const cls = 'nav-sec ' + (isActive(t) ? 'on' : 'quiet')
        const style = { opacity: href ? 1 : 0.35, pointerEvents: href ? 'auto' : 'none', justifyContent: 'flex-start' } as const
        if (!href) return <span key={t.key} className={cls} style={{ ...style, display: 'flex', alignItems: 'center', gap: 8 }} title={`${t.label} (open a case first)`}><span className="icon">{t.icon}</span>{!collapsed && t.label}</span>
        return (
          <NavLink key={t.key} to={href} end={t.key === 'cases'} className={cls} style={{ ...style, display: 'flex', alignItems: 'center', gap: 8 }} title={t.label}>
            <span className="icon">{t.icon}</span>{!collapsed && t.label}
          </NavLink>
        )
      })}
    </nav>
  )
}

export function MobileNav() {
  const loc = useLocation()
  const caseId = currentCaseId(loc.pathname)
  return (
    <div className="lg:hidden flex overflow-x-auto border-b border-line" aria-label="primary">
      {TABS.map((t) => {
        const href = !t.needsCase ? t.path : caseId ? (t.sub ? `/cases/${caseId}/${t.sub}` : `/cases/${caseId}`) : null
        if (!href) return <span key={t.key} className="btn" style={{ opacity: 0.35 }}>{t.label}</span>
        const active = loc.pathname === href || (t.key === 'investigation' && loc.pathname === `/cases/${caseId}`)
        return <NavLink key={t.key} to={href} className={'btn no-underline ' + (active ? 'on' : '')}>{t.icon} {t.label}</NavLink>
      })}
    </div>
  )
}

export function StatusBar() {
  const { health } = useApp()
  const ai = health?.ai?.configured ? `AI ${health.ai.model}` : 'AI UNAVAILABLE'
  const video = health?.video?.provider ? `VIDEO ${String(health.video.provider).toUpperCase()}` : 'VIDEO LOCAL'
  const chain = health?.integrity?.audit_chain
  const integrityVariant = !chain ? 'mut' : chain.ok ? 'ok' : 'crit'
  return (
    <footer className="flex flex-wrap items-center gap-x-3 border-t border-line px-3 py-1 text-[12px]">
      <span>VIVAD</span>|<span>AI ASSISTS · HUMANS DECIDE</span>
      <span className="ml-auto flex items-center gap-2">
        <StatusChip variant={integrityVariant as 'ok' | 'mut' | 'crit'} dot>{!chain ? 'INTEGRITY --' : chain.ok ? 'INTEGRITY OK' : 'INTEGRITY WARNING'}</StatusChip>
        <span className="quiet">{video} · {ai}</span>
      </span>
    </footer>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('vivad-nav-collapsed') === '1' } catch { return false }
  })
  const toggle = () => setCollapsed((c) => {
    const next = !c
    try { localStorage.setItem('vivad-nav-collapsed', next ? '1' : '0') } catch { /* ignore */ }
    return next
  })
  return (
    <div className="grid h-screen w-screen overflow-hidden" style={{ gridTemplateRows: 'auto auto 1fr auto' }}>
      <TopBar />
      <MobileNav />
      <div className="grid min-h-0" style={{ gridTemplateColumns: isDesktop ? (collapsed ? '46px minmax(0,1fr)' : '190px minmax(0,1fr)') : 'minmax(0,1fr)' }}>
        <Sidebar collapsed={collapsed} onToggle={toggle} />
        <main className="overflow-auto p-4 min-w-0">{children}</main>
      </div>
      <StatusBar />
    </div>
  )
}

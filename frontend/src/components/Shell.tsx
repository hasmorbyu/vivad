import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../lib/store'
import { useAuth } from '../lib/auth'
import { api, fmt } from '../lib/api'
import { StatusChip } from './ui'

const NAV: { group: string; items: [string, string, string][] }[] = [
  { group: 'VIVAD', items: [['/dashboard', '01', 'DASHBOARD'], ['/cases', '02', 'CASES'], ['/uploads', '03', 'UPLOADS']] },
]

function NotificationBell() {
  const [unread, setUnread] = useState(0)
  useEffect(() => {
    const load = () => api.get('/notifications').then((d) => setUnread(d.unread)).catch(() => undefined)
    load()
    const t = setInterval(load, 15000)
    return () => clearInterval(t)
  }, [])
  return <NavLink className="btn no-underline" to="/notifications">[ NOTIFICATIONS{unread ? ` · ${unread}` : ''} ]</NavLink>
}

export function TopBar() {
  const { theme, setTheme } = useApp()
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const [q, setQ] = useState('')
  return (
    <header className="flex flex-wrap items-center gap-3 border-b border-line px-3 py-2">
      <NavLink to="/dashboard" className="tracking-[.18em]" style={{ fontWeight: 700, textDecoration: 'none', color: 'inherit' }}>VIVAD</NavLink>
      <span className="lbl hidden sm:inline">AI-ASSISTED PRELIMINARY DISPUTE RESOLUTION</span>
      <form className="flex-1 min-w-[140px] max-w-[380px] ml-auto" onSubmit={(e) => { e.preventDefault(); if (q.trim().length >= 2) { nav(`/search?q=${encodeURIComponent(q.trim())}`) } }}>
        <input className="w-full" placeholder="SEARCH CASES · PARTIES · EVIDENCE · CLAIMS" aria-label="global search" value={q} onChange={(e) => setQ(e.target.value)} />
      </form>
      <NotificationBell />
      <div className="flex gap-1" role="group" aria-label="theme">
        <button className={'btn ' + (theme === 'light' ? 'on' : '')} onClick={() => setTheme('light')} aria-pressed={theme === 'light'}>[ LIGHT ]</button>
        <button className={'btn ' + (theme === 'dark' ? 'on' : '')} onClick={() => setTheme('dark')} aria-pressed={theme === 'dark'}>[ DARK ]</button>
      </div>
      {user && (
        <div className="flex items-center gap-2">
          <span className="lbl">{user.name} · {fmt.label(user.role)}</span>
          <button className="btn" onClick={async () => { await logout(); nav('/login') }}>[ SIGN OUT ]</button>
        </div>
      )}
    </header>
  )
}

export function Sidebar() {
  return (
    <nav className="border-r border-line p-3 hidden lg:block overflow-auto" aria-label="primary">
      {NAV.map((g) => (
        <div key={g.group} className="mb-5">
          <div className="lbl mb-1">{g.group}</div>
          {g.items.map(([to, n, label]) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => 'block px-2 py-[3px] border border-transparent hover:border-line no-underline ' + (isActive ? '' : 'text-mut')}
              style={({ isActive }) => isActive ? { background: 'var(--fg)', color: 'var(--bg)' } : { color: 'inherit' }}>
              {n}&nbsp;&nbsp;{label}
            </NavLink>
          ))}
        </div>
      ))}
      <div className="lbl mt-8">PRINCIPLE</div>
      <div className="text-[12px] leading-6 mt-1">
        <div>AI assists analysis.</div>
        <div className="text-mut">Humans make the final decision.</div>
      </div>
    </nav>
  )
}

export function MobileNav() {
  return (
    <div className="lg:hidden flex flex-wrap border-b border-line">
      {NAV.flatMap((g) => g.items).map(([to, n, l]) => (
        <NavLink key={to} to={to} className="btn no-underline"
          style={({ isActive }) => isActive ? { background: 'var(--fg)', color: 'var(--bg)' } : undefined}>{n} {l}</NavLink>
      ))}
    </div>
  )
}

export function StatusBar() {
  const { health } = useApp()
  const ai = health?.ai?.configured ? `AI ${health.ai.model}` : 'AI UNAVAILABLE'
  const video = health?.video?.provider ? `VIDEO ${String(health.video.provider).toUpperCase()}` : 'VIDEO LOCAL'
  const chain = health?.integrity?.audit_chain
  const integrity = !chain ? 'INTEGRITY --' : chain.ok ? 'INTEGRITY OK' : 'INTEGRITY WARNING'
  const integrityVariant = !chain ? 'mut' : chain.ok ? 'ok' : 'crit'
  return (
    <footer className="flex flex-wrap items-center gap-x-3 border-t border-line px-3 py-1 text-[12px]">
      <span>VIVAD</span>|<span>PRELIMINARY DISPUTE RESOLUTION</span>|<span>AI ASSISTS · HUMANS DECIDE</span>
      <span className="ml-auto flex items-center gap-2">
        <StatusChip variant={integrityVariant as 'ok' | 'mut' | 'crit'} dot>{integrity}</StatusChip>
        <span className="quiet">{video} · {ai}</span>
      </span>
    </footer>
  )
}

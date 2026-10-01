import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import { ErrorBanner } from '../components/ui'

const DEMO: [string, string][] = [
  ['citizen', 'CITIZEN / COMPLAINANT'],
  ['respondent', 'RESPONDENT'],
  ['officer', 'CASE OFFICER'],
  ['reviewer', 'REVIEWER / COMMITTEE'],
  ['chair', 'CHAIR / DECISION MAKER'],
  ['admin', 'ADMINISTRATOR'],
]

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('officer')
  const [password, setPassword] = useState('vivad123')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [target, setTarget] = useState('/dashboard')

  // redirect once signed in, but not mid-action (the demo flow resolves its target first)
  if (user && !busy) return <Navigate to={target} replace />

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr(''); setTarget('/dashboard')
    try { await login(username.trim(), password); nav('/dashboard') }
    catch (x) { setErr((x as Error).message) }
    finally { setBusy(false) }
  }

  async function viewDemo() {
    setBusy(true); setErr('')
    try {
      setTarget('/dashboard')
      await login('officer', 'vivad123')
      const cases: { id: string }[] = await api.get('/cases')
      if (cases.some((c) => c.id === 'VV-2026-00042')) setTarget('/cases/VV-2026-00042')
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="min-h-screen grid place-items-center p-4">
      <div className="w-full max-w-[760px] grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="border border-line p-6">
          <div className="tracking-[.28em] text-[28px]" style={{ fontWeight: 700 }}>VIVAD</div>
          <div className="tracking-[.08em] mt-1">Verified Intake &amp; Validation for Assisted Dispute-resolution</div>
          <hr className="rule" />
          <p className="mb-3">AI-assisted preliminary dispute resolution.</p>
          <div className="border border-line p-3" style={{ borderStyle: 'dashed' }}>
            <div style={{ fontWeight: 700 }}>AI assists analysis.</div>
            <div>Humans make the final decision.</div>
          </div>
          <hr className="rule" />
          <ul className="list-none pl-0 text-[12px] leading-6 text-mut">
            <li>· VIVAD does not replace human judgment.</li>
            <li>· It makes facts, evidence, contradictions and relevant references easier to examine.</li>
            <li>· No AI output becomes a decision without a human action.</li>
          </ul>
        </div>
        <form className="border border-line p-6" onSubmit={submit}>
          <h1 className="text-[16px] tracking-[.16em] uppercase mb-4">Sign in</h1>
          <ErrorBanner message={err} onClose={() => setErr('')} />
          <label className="lbl block mb-1" htmlFor="u">Username</label>
          <input id="u" className="w-full mb-3" value={username} autoComplete="username" onChange={(e) => setUsername(e.target.value)} />
          <label className="lbl block mb-1" htmlFor="p">Password</label>
          <input id="p" className="w-full mb-4" type="password" value={password} autoComplete="current-password" onChange={(e) => setPassword(e.target.value)} />
          <button className="btn w-full" type="submit" disabled={busy || !username || !password}>{busy ? 'SIGNING IN…' : '[ SIGN IN ]'}</button>
          <button className="btn w-full mt-2" type="button" onClick={viewDemo} disabled={busy}>[ VIEW DEMO CASE ]</button>
          <div className="lbl mt-2">DEMO CASE VV-2026-00042 · SYNTHETIC RENTAL DEPOSIT DISPUTE</div>
          <hr className="rule" />
          <div className="lbl mb-1">Demonstration accounts · password “vivad123”</div>
          <div className="flex flex-wrap gap-1">
            {DEMO.map(([u, label]) => (
              <button key={u} type="button" className="btn" onClick={() => { setUsername(u); setPassword('vivad123') }}>{label}</button>
            ))}
          </div>
        </form>
      </div>
    </div>
  )
}

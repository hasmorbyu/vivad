import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import { ErrorBanner } from '../components/ui'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [username, setUsername] = useState('officer')
  const [password, setPassword] = useState('vivad123')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [target, setTarget] = useState('/dashboard')

  // Redirect once signed in
  if (user && !busy) return <Navigate to={target} replace />

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErr('')
    setTarget('/dashboard')
    try {
      await login(username.trim(), password)
      nav('/dashboard')
    } catch (x) {
      setErr((x as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function viewDemo() {
    setBusy(true)
    setErr('')
    try {
      setTarget('/dashboard')
      await login('officer', 'vivad123')
      const cases: { id: string }[] = await api.get('/cases')
      if (cases.some((c) => c.id === 'VV-2026-00042')) {
        setTarget('/cases/VV-2026-00042')
      }
    } catch (x) {
      setErr((x as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen real-wood-bg grid place-items-center p-4 sm:p-8 overflow-y-auto font-mono text-[#1a1612]">
      {/* Container wrapper for folder */}
      <div className="w-full max-w-[880px] relative my-6">
        
        {/* Top Folder Cutout Tabs */}
        <div className="flex items-end gap-1.5 pl-6 -mb-[1px] relative z-0">
          <div className="manila-tab-1 px-5 py-2 text-[12px] tracking-wider uppercase font-bold text-[#2e2316]">
            DOSSIER: VIVAD-MAIN-2026
          </div>
          <div className="manila-tab-2 px-5 py-1.5 text-[11px] tracking-wider uppercase text-[#473722]">
            LEVEL 4 ACCESS
          </div>
        </div>

        {/* Main Manila Cardboard Case File Folder */}
        <div className="manila-cardboard p-5 sm:p-8 relative z-10">
          
          {/* Main 2-Leaf Folder Layout */}
          <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr] relative">
            
            {/* LEFT LEAF: Aged Paper Document Stack */}
            <div className="aged-paper-leaf paper-stack-shadow p-6 sm:p-8 flex flex-col justify-between relative min-h-[460px]">
              <div>
                {/* Header Title */}
                <div className="text-center mt-2 mb-6">
                  <div className="text-[14px] tracking-[.18em] font-bold text-[#2a241b] uppercase">
                    DEPT OF ASSISTED DISPUTE
                  </div>
                  <div className="text-[14px] tracking-[.18em] font-bold text-[#2a241b] uppercase">
                    RESOLUTION
                  </div>
                </div>

                {/* Huge Red Rubber Stamp */}
                <div className="my-8 text-center">
                  <div className="stamp-confidential-red">
                    CONFIDENTIAL
                  </div>
                </div>

                {/* Barcode Graphic */}
                <div className="mt-12 text-center select-none">
                  <div className="inline-block tracking-[-0.05em] text-[26px] font-mono leading-none text-[#1a1612]">
                    ||||| ||| ||||||| || |||| |||||||| ||| |||||
                  </div>
                  <div className="text-[11px] tracking-[.25em] text-[#42392c] mt-1 font-bold">
                    350333338456926
                  </div>
                </div>
              </div>

              {/* Bottom Mandate Statement */}
              <div className="text-center border-t border-[#c5b597] pt-4 mt-6">
                <div className="text-[12px] tracking-[.06em] font-bold leading-tight text-[#2b241b] uppercase">
                  AI ASSISTS ANALYSIS. HUMANS
                </div>
                <div className="text-[12px] tracking-[.06em] font-bold leading-tight text-[#2b241b] uppercase">
                  MAKE THE FINAL DECISION.
                </div>
              </div>
            </div>

            {/* RIGHT LEAF: Officer Clearance Document & Form */}
            <div className="aged-paper-leaf p-6 sm:p-8 flex flex-col justify-between relative min-h-[460px]">
              <form onSubmit={submit} className="flex flex-col justify-between h-full">
                <div>
                  <h2 className="text-[20px] tracking-[.14em] font-bold text-[#1a1612] uppercase mb-4 text-center border-b border-[#c5b597] pb-3">
                    OFFICER CLEARANCE
                  </h2>

                  <ErrorBanner message={err} onClose={() => setErr('')} />

                  <div className="space-y-4 my-4">
                    <div>
                      <label className="text-[12px] tracking-[.12em] font-bold text-[#2e261d] uppercase block mb-1.5" htmlFor="u">
                        Officer Identifier
                      </label>
                      <input
                        id="u"
                        className="w-full bg-[#eee5d3] border-2 border-[#b8a788] text-[#1a1612] px-3 py-2 text-[14px] font-mono focus:border-[#2e261d] focus:bg-[#f7f0e1] outline-none"
                        value={username}
                        autoComplete="username"
                        onChange={(e) => setUsername(e.target.value)}
                      />
                    </div>

                    <div>
                      <label className="text-[12px] tracking-[.12em] font-bold text-[#2e261d] uppercase block mb-1.5" htmlFor="p">
                        Passcode
                      </label>
                      <input
                        id="p"
                        type="password"
                        className="w-full bg-[#eee5d3] border-2 border-[#b8a788] text-[#1a1612] px-3 py-2 text-[14px] font-mono focus:border-[#2e261d] focus:bg-[#f7f0e1] outline-none"
                        value={password}
                        autoComplete="current-password"
                        onChange={(e) => setPassword(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                {/* Buttons Section matching the reference metallic button */}
                <div className="space-y-3 mt-6">
                  <button
                    type="submit"
                    className="metallic-button w-full py-3.5 px-4 text-[13px] tracking-[.16em] font-bold uppercase cursor-pointer block text-center"
                    disabled={busy || !username || !password}
                  >
                    {busy ? 'VERIFYING CLEARANCE…' : 'AUTHORIZE CLEARANCE & SIGN IN'}
                  </button>

                  <button
                    type="button"
                    className="w-full py-2 px-3 text-[11px] tracking-[.1em] font-bold uppercase border border-[#a89574] bg-[#eae0cc] text-[#3d3224] hover:bg-[#ded1b8] cursor-pointer"
                    onClick={viewDemo}
                    disabled={busy}
                  >
                    [ OPEN DEMO CASE VV-2026-00042 ]
                  </button>
                </div>

                <div className="text-[10px] tracking-wider text-[#6b5d4a] uppercase text-center mt-4 border-t border-[#c5b597] pt-2">
                  SECURE SYSTEM SESSION · VV-AMADEUS-2026
                </div>
              </form>
            </div>

          </div>

        </div>

      </div>
    </div>
  )
}

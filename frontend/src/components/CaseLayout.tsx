import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useOutletContext, useParams } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { useApp } from '../lib/store'
import { Empty, ErrorBanner, Loading } from './ui'
import type { J } from '../types'

export interface CaseCtx {
  caseData: J
  reload: () => void
  setCaseData: (c: J) => void
}

export const useCase = () => useOutletContext<CaseCtx>()

const TABS: [string, string][] = [
  ['', 'OVERVIEW'],
  ['parties', 'PARTIES'],
  ['statements', 'STATEMENTS'],
  ['evidence', 'EVIDENCE'],
  ['timeline', 'TIMELINE'],
  ['claims', 'CLAIMS'],
  ['contradictions', 'CONTRADICTIONS'],
  ['legal', 'LEGAL'],
  ['graph', 'GRAPH'],
  ['hearings', 'HEARINGS'],
  ['review', 'REVIEW'],
  ['decision', 'DECISION'],
  ['audit', 'AUDIT'],
  ['report', 'REPORT'],
]

export default function CaseLayout() {
  const { caseId } = useParams<{ caseId: string }>()
  const { version, bump } = useApp()
  const [caseData, setCaseData] = useState<J>(null)
  const [err, setErr] = useState('')
  const [notFound, setNotFound] = useState(false)

  const reload = useCallback(() => {
    if (!caseId) return
    api.get(`/cases/${caseId}`).then((d) => { setCaseData(d); setNotFound(false) })
      .catch((e) => { setErr((e as Error).message); setNotFound(true) })
  }, [caseId])
  useEffect(() => { reload() }, [reload, version])

  if (notFound) return <Empty>Case not found or you do not have access to it.</Empty>
  if (!caseData) return <Loading what="LOADING CASE" />

  return (
    <div>
      <div className="border border-line p-3 mb-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-[18px] tracking-[.06em]">{caseData.id}</span>
              {caseData.synthetic ? <span className="lbl">SYNTHETIC</span> : null}
            </div>
            <div className="text-[15px] tracking-[.08em]">{caseData.title}</div>
            <div className="lbl mt-1">{fmt.label(caseData.category)} · {caseData.party_summary || 'no parties yet'}</div>
          </div>
          <div className="text-right">
            <div className="lbl">Status</div>
            <div>{fmt.label(caseData.status)}</div>
            <div className="lbl mt-1">Next action</div>
            <div className="text-[12px]">{caseData.next_action}</div>
          </div>
        </div>
      </div>
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <nav className="flex flex-wrap gap-1 border-b border-line mb-4 pb-1" aria-label="case sections">
        {TABS.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === ''}
            className={({ isActive }) => 'btn no-underline ' + (isActive ? 'on' : '')}>
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet context={{ caseData, reload, setCaseData } satisfies CaseCtx} />
      <div className="mt-6">
        <button className="btn" onClick={() => bump()}>[ REFRESH COUNTS ]</button>
      </div>
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useOutletContext, useParams } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { useApp } from '../lib/store'
import { caseStatusVariant } from '../lib/semantics'
import { Empty, ErrorBanner, Loading, StatusChip } from './ui'
import type { J } from '../types'

export interface CaseCtx {
  caseData: J
  reload: () => void
  setCaseData: (c: J) => void
}

export const useCase = () => useOutletContext<CaseCtx>()

// Five destinations instead of fifteen. Sub-sections appear only for the active area.
const SECTIONS: { key: string; label: string; icon: string; items: [string, string, string][] }[] = [
  { key: 'overview', label: 'Overview', icon: '◈', items: [['', 'Overview', '◈']] },
  { key: 'case', label: 'Case', icon: '◉', items: [['parties', 'Parties', '●'], ['statements', 'Statements', '¶'], ['claims', 'Claims', '⚑']] },
  { key: 'evidence', label: 'Evidence', icon: '▣', items: [['evidence', 'Evidence', '▣'], ['timeline', 'Timeline', '⌁'], ['graph', 'Graph', '◎']] },
  { key: 'analysis', label: 'Analysis', icon: '⚠', items: [['contradictions', 'Contradictions', '⚠'], ['legal', 'Legal', '§']] },
  { key: 'process', label: 'Process', icon: '◷', items: [['hearings', 'Hearings', '◷'], ['review', 'Review', '✓'], ['decision', 'Decision', '⚖'], ['audit', 'Audit', '⛓'], ['report', 'Report', '▤']] },
]

function sectionFor(path: string, caseId: string): string {
  const base = `/cases/${caseId}`
  if (path === base || path === base + '/') return 'overview'
  for (const s of SECTIONS) {
    for (const [to] of s.items) {
      if (to && path.startsWith(`${base}/${to}`)) return s.key
    }
  }
  return 'overview'
}

export default function CaseLayout() {
  const { caseId } = useParams<{ caseId: string }>()
  const { version, bump } = useApp()
  const loc = useLocation()
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

  const active = sectionFor(loc.pathname, caseData.id)
  const section = SECTIONS.find((s) => s.key === active) || SECTIONS[0]

  return (
    <div>
      <div className="border-b border-line pb-3 mb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="lbl">{caseData.id}</span>
              {caseData.synthetic ? <StatusChip variant="mut">SYNTHETIC</StatusChip> : null}
              <StatusChip variant={caseStatusVariant(caseData.status)} solid dot>{fmt.label(caseData.status)}</StatusChip>
            </div>
            <h1 className="title mt-1">{caseData.title}</h1>
            <div className="quiet tiny">{fmt.label(caseData.category)} · {caseData.party_summary || 'no parties yet'}</div>
          </div>
          <div className="text-right shrink-0">
            <div className="lbl">Next action</div>
            <div className="text-[12px]">{caseData.next_action}</div>
          </div>
        </div>
      </div>

      <ErrorBanner message={err} onClose={() => setErr('')} />

      <nav className="flex flex-wrap items-center gap-2 mb-2" aria-label="case sections">
        {SECTIONS.map((s) => (
          <NavLink key={s.key} to={s.key === 'overview' ? '' : s.items[0][0]} end={s.key === 'overview'}
            className={'nav-sec ' + (active === s.key ? 'on' : 'quiet')}>
            <span className="icon">{s.icon}</span> {s.label}
          </NavLink>
        ))}
      </nav>

      <div className="flex flex-wrap gap-1 border-b border-line pb-2 mb-4" aria-label={`${section.label} sections`}>
        {section.items.length > 1 && section.items.map(([to, label, icon]) => (
          <NavLink key={to} to={to} end={to === ''} className={({ isActive }) => 'nav-sub ' + (isActive ? 'on' : '')}>
            <span className="icon">{icon}</span> {label}
          </NavLink>
        ))}
      </div>

      <Outlet context={{ caseData, reload, setCaseData } satisfies CaseCtx} />
      <div className="mt-6">
        <button className="btn btn-quiet" onClick={() => bump()}>[ REFRESH ]</button>
      </div>
    </div>
  )
}

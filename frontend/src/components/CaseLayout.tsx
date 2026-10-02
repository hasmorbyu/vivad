import { useCallback, useEffect, useState } from 'react'
import { Outlet, useOutletContext, useParams } from 'react-router-dom'
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

export default function CaseLayout() {
  const { caseId } = useParams<{ caseId: string }>()
  const { version } = useApp()
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
      <div className="border-b border-line pb-3 mb-4">
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
      <Outlet context={{ caseData, reload, setCaseData } satisfies CaseCtx} />
    </div>
  )
}

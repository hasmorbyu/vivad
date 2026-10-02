import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useMediaQuery } from '../../lib/useMediaQuery'
import { JourneyMap } from '../../components/JourneyMap'
import { JourneyDetail } from '../../components/JourneyDetail'
import { Empty, ErrorBanner, Loading } from '../../components/ui'
import type { J } from '../../types'

const FILTERS = ['ALL', 'COMPLETED', 'CURRENT', 'UPCOMING']

export default function Journey() {
  const { caseData } = useCase()
  const nav = useNavigate()
  const cid = caseData.id
  const vertical = useMediaQuery('(max-width: 1023px)')
  const [data, setData] = useState<J>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState('ALL')
  const [showToday, setShowToday] = useState(true)
  const [err, setErr] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const load = useCallback(() => {
    api.get(`/cases/${cid}/journey`).then((d) => {
      setData(d)
      setSelectedId((cur) => cur ?? d.stages.find((s: J) => s.status === 'CURRENT')?.id ?? d.stages[0]?.id ?? null)
    }).catch((e) => setErr((e as Error).message))
  }, [cid])
  useEffect(() => { load() }, [load])

  const stages: J[] = data?.stages || []
  const selected = stages.find((s) => s.id === selectedId) || null
  const selIdx = stages.findIndex((s) => s.id === selectedId)
  const prev = selIdx > 0 ? stages[selIdx - 1] : undefined
  const next = selIdx >= 0 && selIdx < stages.length - 1 ? stages[selIdx + 1] : undefined
  const currentId = stages.find((s) => s.status === 'CURRENT')?.id ?? null

  const scrollTo = useCallback((id: string | null) => {
    if (!id) return
    requestAnimationFrame(() => {
      const el = scrollRef.current?.querySelector(`.jnode[data-stage="${id}"]`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
    })
  }, [])
  const select = useCallback((s: J) => { setSelectedId(s.id); scrollTo(s.id) }, [scrollTo])

  if (err) return <Empty>{err}</Empty>
  if (!data) return <Loading what="BUILDING CASE JOURNEY" />
  return (
    <div>
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <SectionHeader data={data} />

      <div className="flex flex-wrap items-center gap-2 mb-2">
        <div className="flex gap-1" role="group" aria-label="filter by status">
          {FILTERS.map((f) => <button key={f} className={'btn ' + (filter === f ? 'on' : '')} onClick={() => setFilter(f)}>[ {f} ]</button>)}
        </div>
        <button className="btn" onClick={() => { setSelectedId(currentId ?? null); scrollTo(currentId ?? null) }} disabled={!currentId}>[ JUMP TO CURRENT ]</button>
        <button className={'btn ' + (showToday ? 'on' : '')} onClick={() => setShowToday((v) => !v)} aria-pressed={showToday}>[ TODAY ]</button>
        <div className="flex gap-1 ml-auto">
          <button className="btn" onClick={() => prev && select(prev)} disabled={!prev}>[ ◀ PREV ]</button>
          <span className="lbl self-center">{selIdx >= 0 ? `STAGE ${selIdx + 1} / ${stages.length}` : `${stages.length} STAGES`}</span>
          <button className="btn" onClick={() => next && select(next)} disabled={!next}>[ NEXT ▶ ]</button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="min-w-0">
          <JourneyMap stages={stages} selectedId={selectedId} filter={filter} showToday={showToday} vertical={vertical}
            scrollRef={scrollRef} onSelect={select}
            onOpenEvidence={(id) => nav(`/cases/${cid}/evidence/${id}`)}
            onOpenParticipants={() => nav(`/cases/${cid}/parties`)}
            onOpenEvidenceGroup={() => nav(`/cases/${cid}/evidence`)} />
          <div className="lbl mt-1">
            ● COMPLETED · ◉ CURRENT · ○ UPCOMING · ▣ ATTENTION · ◌ PENDING · PATH STRONGER BEHIND, SUBDUED AHEAD
          </div>
        </div>
        {selected && (
          <JourneyDetail caseId={cid} stage={selected} prev={prev} next={next} onSelect={select}
            onOpenEvidence={(id) => nav(`/cases/${cid}/evidence/${id}`)}
            onOpenParticipants={() => nav(`/cases/${cid}/parties`)} onClose={() => setSelectedId(null)} />
        )}
      </div>
    </div>
  )
}

function SectionHeader({ data }: { data: J }) {
  const h = data.header
  const c = h.counts
  return (
    <div className="border border-line p-3 mb-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <div className="text-[18px] tracking-[.06em]">{h.case_id}</div>
          <div className="lbl">DISPUTE PROGRESSION · {data.case.category_label}{data.case.synthetic ? ' · SYNTHETIC' : ''}</div>
        </div>
        <div className="flex flex-wrap gap-x-4 text-[13px]">
          <span style={{ color: 'var(--ok)' }}>● {c.completed} Completed</span>
          <span style={{ color: 'var(--accent)', fontWeight: 700 }}>◉ {c.current} Current</span>
          <span className="text-mut">○ {c.upcoming} Upcoming</span>
        </div>
      </div>
      <hr className="rule" />
      <div className="grid gap-3 sm:grid-cols-3">
        <div><div className="lbl">Current stage</div><div>{fmt.label(h.current_stage)}</div></div>
        <div><div className="lbl">Next action</div><div>{h.next_action || '—'}</div></div>
        <div><div className="lbl">Due</div><div>{h.due_date ? fmt.date(h.due_date) : '—'}</div></div>
      </div>
    </div>
  )
}

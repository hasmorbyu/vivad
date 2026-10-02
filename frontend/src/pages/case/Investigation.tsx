import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Metric, Section, StatusChip } from '../../components/ui'
import Parties from './Parties'
import Statements from './Statements'
import Evidence from './Evidence'
import Claims from './Claims'
import TimelineTab from './TimelineTab'
import Contradictions from './Contradictions'
import Legal from './Legal'
import type { J } from '../../types'

const SECTIONS = [
  ['case-file', 'Case file'], ['evidence', 'Evidence'], ['claims', 'Claims'],
  ['timeline', 'Events timeline'], ['pre-hearing', 'Pre-hearing'],
]

export default function Investigation() {
  const { caseData } = useCase()
  const cid = caseData.id
  const [contradictions, setContradictions] = useState<J[]>([])
  const [analysis, setAnalysis] = useState<J>(null)

  useEffect(() => {
    api.get(`/cases/${cid}/contradictions`).then(setContradictions).catch(() => undefined)
    api.get(`/cases/${cid}/analysis`).then(setAnalysis).catch(() => undefined)
  }, [cid])

  const s = caseData.stats
  const openContra = contradictions.filter((c) => c.verification_status === 'REQUIRES_HUMAN_REVIEW').length
  const summary = oneLine(caseData.summary_text) || caseData.description || caseData.title
  const out = analysis?.analysis || {}

  return (
    <div className="max-w-[1150px]">
      <div className="mb-4">
        <div className="lbl">Investigation summary</div>
        <p className="text-[15px]" style={{ fontWeight: 700 }}>{summary}</p>
      </div>

      <Section title="At a glance">
        <div className="flex flex-wrap border border-line">
          <Metric value={fmt.n(s.parties)} label="Parties" icon="●" />
          <Metric value={fmt.n(s.claims)} label="Issues / claims" icon="⚑" />
          <Metric value={fmt.n(contradictions.length)} label="Contradictions" icon="⚠" variant={openContra > 0 ? 'crit' : undefined} />
          <Metric value={fmt.n(s.evidence)} label="Evidence" icon="▣" />
          <Metric value={fmt.n(s.events)} label="Events" icon="⌁" />
          <Metric value={fmt.n(s.legal_refs)} label="Legal refs" icon="§" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 mt-3">
          <div>
            <div className="lbl mb-1">Parties</div>
            <div>{caseData.party_summary || '—'}</div>
          </div>
          <div>
            <div className="lbl mb-1">Status / issue</div>
            <div><StatusChip variant={openContra > 0 ? 'crit' : 'ok'}>{openContra > 0 ? `${openContra} open contradiction(s)` : 'no open contradictions'}</StatusChip></div>
          </div>
        </div>
      </Section>

      <nav className="flex flex-wrap gap-1 mb-4" aria-label="investigation sections">
        {SECTIONS.map(([id, label]) => (
          <a key={id} href={`#${id}`} className="nav-sub">{label}</a>
        ))}
      </nav>

      <section id="case-file" className="scroll-mt-2">
        <h2 className="text-[14px] tracking-[.14em] uppercase border-b border-line pb-1 mb-3">Case file</h2>
        <div className="grid gap-6 xl:grid-cols-2">
          <Parties />
          <Statements />
        </div>
      </section>

      <section id="evidence" className="scroll-mt-2 mt-8">
        <Evidence />
      </section>

      <section id="claims" className="scroll-mt-2 mt-8">
        <Claims />
      </section>

      <section id="timeline" className="scroll-mt-2 mt-8">
        <TimelineTab />
      </section>

      <section id="pre-hearing" className="scroll-mt-2 mt-8">
        <h2 className="text-[14px] tracking-[.14em] uppercase border-b border-line pb-1 mb-3">Pre-hearing</h2>
        {(out.missing_information?.length > 0 || out.hearing_questions?.length > 0 || out.claims_requiring_verification?.length > 0) && (
          <div className="grid gap-4 lg:grid-cols-3 mb-6">
            <div>
              <div className="lbl mb-1">Evidence gaps</div>
              {(out.missing_information || []).length === 0 ? <span className="quiet tiny">none</span> :
                (out.missing_information || []).map((m: J, i: number) => <div key={i} className="tiny border-b border-soft py-1">{m.text}</div>)}
            </div>
            <div>
              <div className="lbl mb-1">Points to clarify</div>
              {(out.hearing_questions || []).length === 0 ? <span className="quiet tiny">none</span> :
                (out.hearing_questions || []).map((q: string, i: number) => <div key={i} className="tiny border-b border-soft py-1">{q}</div>)}
            </div>
            <div>
              <div className="lbl mb-1">Unresolved questions</div>
              {(out.claims_requiring_verification || []).length === 0 ? <span className="quiet tiny">none</span> :
                (out.claims_requiring_verification || []).map((c: J, i: number) => <div key={i} className="tiny border-b border-soft py-1">{c.text} <span className="quiet">· {c.reason}</span></div>)}
            </div>
          </div>
        )}
        <div className="grid gap-6 xl:grid-cols-2">
          <Contradictions />
          <Legal />
        </div>
      </section>

      <div className="mt-6">
        <Link className="btn no-underline" to={`/cases/${cid}/review`}>[ GO TO REVIEW &amp; RESOLUTION ]</Link>
      </div>
    </div>
  )
}

function oneLine(text?: string | null): string {
  if (!text) return ''
  const first = text.split('\n')[0].trim()
  const sentence = first.split(/(?<=\.)\s/)[0]
  return sentence.length > 220 ? sentence.slice(0, 217) + '…' : sentence
}

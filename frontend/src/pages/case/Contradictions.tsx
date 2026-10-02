import { useCallback, useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Loading, Section, StatusChip } from '../../components/ui'
import { contradictionVariant } from '../../lib/semantics'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

const STATUS: [string, string][] = [
  ['CONFIRMED_INCONSISTENCY', 'CONFIRM'],
  ['DISMISSED', 'DISMISS'],
  ['ESCALATED', 'ESCALATE'],
]

export default function Contradictions() {
  const { caseData } = useCase()
  const [rows, setRows] = useState<J[] | null>(null)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    api.get(`/cases/${caseData.id}/contradictions`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [caseData.id])
  useEffect(() => { load() }, [load])

  async function review(ref: string, status: string) {
    try { await api.patch(`/cases/${caseData.id}/contradictions/${ref}`, { verification_status: status }); load() }
    catch (e) { setErr((e as Error).message) }
  }

  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Potential contradictions · ${rows?.length ?? 0}`}>
        {rows === null ? <Loading /> : rows.length === 0 ? <Empty>None detected. Run analysis; VIVAD flags possible inconsistencies for human review.</Empty> : (
          <div className="grid gap-4">
            {rows.map((c) => (
              <article key={c.id} className="border border-line p-3">
                <div className="flex flex-wrap items-center gap-2 border-b border-soft pb-1 mb-2">
                  <span style={{ fontWeight: 700 }}>{c.contradiction_ref}</span>
                  <span className="lbl">{c.kind_label}</span>
                  <span className="lbl ml-auto">BASIS · {c.confidence || '—'}</span>
                </div>
                <p style={{ fontWeight: 700 }}>{c.title}</p>
                <div className="grid gap-3 sm:grid-cols-2 my-2">
                  {['a', 'b'].map((side) => c[`claim_${side}`] && (
                    <div key={side} className="border border-soft p-2">
                      <div className="lbl">{c[`claim_${side}`].party_name || 'PARTY'} · {c[`claim_${side}`].claim_ref}</div>
                      <div>{c[`claim_${side}`].text}</div>
                    </div>
                  ))}
                </div>
                <div className="lbl">Evidence</div>
                <div className="flex flex-wrap gap-x-2 mb-2">
                  {c.evidence.length === 0 ? <span className="text-mut">none directly cited</span> :
                    c.evidence.map((e: J, i: number) => e.evidence_ref ? <EvidenceRef key={i} caseId={caseData.id} id={e.id} ref_={e.evidence_ref} /> : null)}
                </div>
                <div className="lbl">Analysis</div>
                <p>{c.explanation}</p>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <StatusChip variant={contradictionVariant(c.verification_status)}>{c.verification_status.replaceAll('_', ' ')}</StatusChip>
                  {c.verification_status === 'REQUIRES_HUMAN_REVIEW' && STATUS.map(([s, label]) => (
                    <button key={s} className="btn" onClick={() => review(c.contradiction_ref, s)}>[ {label} ]</button>
                  ))}
                  {c.verification_status !== 'REQUIRES_HUMAN_REVIEW' && (
                    <button className="btn" onClick={() => review(c.contradiction_ref, 'REQUIRES_HUMAN_REVIEW')}>[ RESET ]</button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </Section>
      <div className="lbl">A POTENTIAL CONTRADICTION IS AN INCONSISTENCY FOR A HUMAN TO RESOLVE. IT DOES NOT ESTABLISH THAT ANY PARTY IS UNTRUTHFUL.</div>
    </div>
  )
}

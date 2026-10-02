import { Link } from 'react-router-dom'
import { fmt } from '../lib/api'
import { Field, StatusChip, TrustTag } from './ui'
import type { J } from '../types'

const OPEN_TAB: Record<string, [string, string]> = {
  FILED: ['parties', 'OPEN IN CASE'],
  PARTIES: ['parties', 'VIEW PARTIES'],
  STATEMENTS: ['statements', 'VIEW STATEMENTS'],
  EVIDENCE_SUBMITTED: ['evidence', 'VIEW EVIDENCE'],
  ANALYSIS: ['claims', 'VIEW CLAIMS'],
  CONTRADICTIONS: ['contradictions', 'VIEW CONTRADICTIONS'],
  HUMAN_REVIEW: ['review', 'VIEW REVIEW'],
  EVIDENCE_REQUEST: ['review', 'VIEW REQUESTS'],
  HEARING: ['hearings', 'VIEW HEARINGS'],
  DECISION: ['decision', 'VIEW DECISION'],
  RESOLUTION: ['decision', 'RECORD DECISION'],
}

interface Props {
  caseId: string
  stage: J
  prev?: J
  next?: J
  onSelect: (s: J) => void
  onOpenEvidence: (id: number) => void
  onOpenParticipants: () => void
  onClose: () => void
}

export function JourneyDetail({ caseId, stage, prev, next, onSelect, onOpenEvidence, onOpenParticipants, onClose }: Props) {
  const open = OPEN_TAB[stage.kind] || ['overview', 'OPEN IN CASE']
  const trust = stage.source === 'decision' || stage.source === 'reviews' ? 'HUMAN' : stage.source === 'evidence' ? 'EVIDENCE' : 'AI'
  return (
    <aside className="border border-line p-3">
      <div className="flex items-start justify-between gap-2 border-b border-line pb-1 mb-2">
        <div>
          <div className="lbl">{stage.kind.replaceAll('_', ' ')}{stage.recordRef ? ` · ${stage.recordRef}` : ''}</div>
          <h3 className="text-[14px]">{stage.title}</h3>
        </div>
        <button className="btn" onClick={onClose} aria-label="close detail">×</button>
      </div>

      <div className="flex flex-wrap items-center gap-2 mb-2">
        <StatusChip variant={stage.status === 'COMPLETED' ? 'ok' : stage.status === 'CURRENT' ? 'accent' : 'mut'}>{stage.status}</StatusChip>
        {stage.flag === 'CRITICAL' && <StatusChip variant="crit">▣ ATTENTION</StatusChip>}
        {stage.flag === 'BLOCKED' && <StatusChip variant="warn">◌ PENDING</StatusChip>}
        <span className="ml-auto"><TrustTag label={trust} /></span>
      </div>

      <Field k="Date and time">{stage.date ? `${fmt.date(stage.date)}${stage.date.length > 10 ? ' · ' + fmt.clock(stage.date) : ' (date only)'}` : 'Date pending'}</Field>
      {stage.description && <Field k="Description">{stage.description}</Field>}
      {stage.flagReason && <Field k="Condition">{stage.flagReason}</Field>}
      {stage.actionRequired && <Field k="Action required">{stage.actionRequired}{stage.dueDate ? ` · due ${fmt.date(stage.dueDate)}` : ''}</Field>}

      <Field k={`Participants (${stage.participants.length})`}>
        {stage.participants.length === 0 ? <span className="text-mut">none recorded</span> : (
          <div className="grid gap-1">
            {stage.participants.map((p: J, i: number) => (
              <button key={i} className="link text-left" onClick={onOpenParticipants}>{p.name}{p.role ? ` · ${p.role}` : ''}{p.attended ? ' ✓' : ''}</button>
            ))}
          </div>
        )}
      </Field>

      <Field k={`Evidence (${stage.evidence.length})`}>
        {stage.evidence.length === 0 ? <span className="text-mut">none attached</span> : (
          <div className="flex flex-wrap gap-x-2">
            {stage.evidence.map((e: J, i: number) => (
              <button key={i} className="link" onClick={() => onOpenEvidence(e.id)}>[{e.evidence_ref}] {e.filename}</button>
            ))}
          </div>
        )}
      </Field>

      {stage.legalReferences.length > 0 && (
        <Field k="Legal references">
          <div className="grid gap-1">
            {stage.legalReferences.map((l: J) => (
              <Link key={l.id} className="link" to={`/cases/${caseId}/legal`}>{l.act} · s.{l.section} — {l.title}</Link>
            ))}
          </div>
        </Field>
      )}

      {stage.relatedEvents?.length > 0 && (
        <Field k="Related events">
          <div className="grid gap-1">
            {stage.relatedEvents.map((r: J, i: number) => <Link key={i} className="link" to={`/cases/${caseId}/contradictions`}>{r.id} · {r.title}</Link>)}
          </div>
        </Field>
      )}

      <div className="flex flex-wrap gap-2 mt-2">
        <Link className="btn no-underline" to={`/cases/${caseId}/${open[0]}`}>[ {open[1]} ]</Link>
      </div>

      <hr className="rule" />
      <div className="flex justify-between gap-2">
        <button className="btn" disabled={!prev} onClick={() => prev && onSelect(prev)}>◀ {prev ? prev.title : 'START'}</button>
        <button className="btn" disabled={!next} onClick={() => next && onSelect(next)}>{next ? next.title : 'END'} ▶</button>
      </div>
      <div className="lbl mt-2">SOURCE · {stage.source || 'case record'}{stage.recordRef ? ` · ${stage.recordRef}` : ''}</div>
    </aside>
  )
}

import { fmt } from '../lib/api'
import type { J } from '../types'

const KIND_LABEL: Record<string, string> = {
  FILED: 'CASE FILED', PARTIES: 'PARTIES', STATEMENTS: 'STATEMENTS', EVIDENCE_SUBMITTED: 'EVIDENCE SUBMITTED',
  ANALYSIS: 'ANALYSIS', CONTRADICTIONS: 'CONTRADICTIONS', HUMAN_REVIEW: 'HUMAN REVIEW',
  EVIDENCE_REQUEST: 'EVIDENCE REQUEST', HEARING: 'HEARING', DECISION: 'DECISION', RESOLUTION: 'RESOLUTION',
}

export function statusClass(stage: J): string {
  const parts = ['jnode', `jnode-${String(stage.status).toLowerCase()}`]
  if (stage.flag === 'CRITICAL') parts.push('jnode-flag-critical')
  if (stage.flag === 'BLOCKED') parts.push('jnode-flag-blocked')
  return parts.join(' ')
}

export function statusMarker(stage: J) {
  if (stage.status === 'COMPLETED') return <span>[✓] COMPLETED</span>
  if (stage.status === 'CURRENT') return <span style={{ fontWeight: 700 }}>◉ CURRENT</span>
  return <span className="text-mut">○ UPCOMING</span>
}

interface Props {
  stage: J
  selected: boolean
  dim: boolean
  vertical?: boolean
  onSelect: (s: J) => void
  onOpenEvidence: (id: number) => void
  onOpenParticipants: () => void
  onOpenEvidenceGroup: () => void
}

export function JourneyNode({ stage, selected, dim, vertical, onSelect, onOpenEvidence, onOpenParticipants, onOpenEvidenceGroup }: Props) {
  const cls = [statusClass(stage), selected ? 'jnode-selected' : '', dim ? 'jnode-dim' : ''].join(' ')
  const when = stage.date ? `${fmt.date(stage.date)}${stage.date.length > 10 ? ' · ' + fmt.clock(stage.date) : ''}` : 'DATE PENDING'
  return (
    <article className={cls} data-stage={stage.id} style={vertical ? undefined : { width: '100%' }} tabIndex={0} role="button"
      aria-label={`${KIND_LABEL[stage.kind] || stage.kind}: ${stage.title}`}
      onClick={() => onSelect(stage)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(stage) } }}>
      {stage.status === 'CURRENT' && <span className="jpulse" aria-hidden="true" />}
      <div className="border-b border-soft px-2 py-1 flex items-center gap-2">
        <span className="lbl">{KIND_LABEL[stage.kind] || stage.kind}</span>
        {stage.flag === 'CRITICAL' && <span className="lbl" style={{ fontWeight: 700 }}>▣ ATTENTION</span>}
        {stage.flag === 'BLOCKED' && <span className="lbl">◌ PENDING</span>}
        <span className="lbl ml-auto">{statusMarker(stage)}</span>
      </div>
      <div className="px-2 py-1">
        <div className="lbl">{when}</div>
        <div style={{ fontWeight: 700, lineHeight: 1.25 }}>{stage.title}</div>
        {stage.subtitle && <div className="text-[12px] text-mut">{stage.subtitle}</div>}
        <div className="flex flex-wrap gap-x-3 mt-1 text-[11px]">
          {stage.evidence?.length > 0 && (
            <button className="link" onClick={(e) => { e.stopPropagation(); onOpenEvidence(stage.evidence[0].id) }}>
              {stage.evidence.length} Evidence
            </button>
          )}
          {stage.participants?.length > 0 && (
            <button className="link" onClick={(e) => { e.stopPropagation(); onOpenParticipants() }}>
              {stage.participants.length} Participants
            </button>
          )}
        </div>
        {stage.flagReason && (
          <div className="text-[11px] mt-1" style={{ borderTop: '1px dotted var(--soft)', paddingTop: 2 }}>
            {stage.flag === 'CRITICAL' ? 'ATTENTION · ' : 'PENDING · '}{stage.flagReason}
          </div>
        )}
        {stage.branches?.length > 0 && (
          <div className="mt-2 jbranch">
            <div className="lbl mb-1">Evidence branches</div>
            <div className="flex flex-wrap gap-1">
              {stage.branches.map((b: J) => (
                <button key={b.id} className="jchip" onClick={(e) => { e.stopPropagation(); onOpenEvidenceGroup() }}>
                  {b.label} · {b.count}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </article>
  )
}

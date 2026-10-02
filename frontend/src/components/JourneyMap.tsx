import { type RefObject } from 'react'
import { JourneyNode } from './JourneyNode'
import type { J } from '../types'

const NODE_W = 220
const GAP = 120
const SPACING = NODE_W + GAP
const MARGIN = 150
const PATH_Y = 270
const WAVE = 40
const CONN = 14
const CANVAS_H = 580

function segStroke(status: string) {
  if (status === 'COMPLETED') return { stroke: 'var(--fg)', width: 3, dash: '' }
  if (status === 'CURRENT') return { stroke: 'var(--fg)', width: 4, dash: '' }
  return { stroke: 'var(--mut)', width: 1.5, dash: '6 5' }
}

function wavePoints(stages: J[]) {
  return stages.map((_, i: number) => ({ x: MARGIN + i * SPACING, y: PATH_Y + (i % 2 === 0 ? -WAVE : WAVE) }))
}

// Catmull-Rom -> cubic bezier, one smooth segment at a time so each can be styled by state.
function segPath(pts: { x: number; y: number }[], i: number): string {
  const p0 = pts[i - 1] || pts[i]
  const p1 = pts[i]
  const p2 = pts[i + 1]
  const p3 = pts[i + 2] || p2
  const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6
  const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6
  return `M ${p1.x} ${p1.y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2.x} ${p2.y}`
}

function todayFraction(stages: J[]): number | null {
  const today = new Date().toISOString().slice(0, 10)
  const dated = stages.map((s, i) => ({ d: (s.date || '').slice(0, 10), i })).filter((x) => x.d)
  if (!dated.length) return null
  const next = dated.find((x) => x.d > today)
  if (next) return next.i
  return dated[dated.length - 1].i + 1
}

interface Props {
  stages: J[]
  selectedId: string | null
  filter: string
  showToday: boolean
  vertical: boolean
  scrollRef: RefObject<HTMLDivElement | null>
  onSelect: (s: J) => void
  onOpenEvidence: (id: number) => void
  onOpenParticipants: () => void
  onOpenEvidenceGroup: () => void
}

export function JourneyMap({ stages, selectedId, filter, showToday, vertical, scrollRef, onSelect, onOpenEvidence, onOpenParticipants, onOpenEvidenceGroup }: Props) {
  const dim = (s: J) => filter !== 'ALL' && s.status !== filter
  const tf = showToday ? todayFraction(stages) : null

  if (vertical) {
    return (
      <div className="relative">
        {stages.map((s, i) => {
          const stroke = s.status === 'UPCOMING' ? '1px dashed var(--mut)' : '2px solid var(--fg)'
          return (
            <div key={s.id}>
              {tf === i && <TodayRow />}
              <div className="flex gap-2 items-stretch">
                <div className="relative shrink-0" style={{ width: 36 }}>
                  {i > 0 && <div className="absolute" style={{ left: 17, top: 0, height: 14, borderLeft: stroke }} />}
                  {i < stages.length - 1 && <div className="absolute" style={{ left: 17, top: 26, bottom: 0, borderLeft: stroke }} />}
                  <div className={`jdot jdot-${String(s.status).toLowerCase()}`} style={{ position: 'absolute', left: 11, top: 14 }} />
                </div>
                <div className="flex-1 min-w-0 pb-4">
                  <JourneyNode stage={s} selected={selectedId === s.id} dim={dim(s)} vertical
                    onSelect={onSelect} onOpenEvidence={onOpenEvidence} onOpenParticipants={onOpenParticipants} onOpenEvidenceGroup={onOpenEvidenceGroup} />
                </div>
              </div>
            </div>
          )
        })}
        {tf === stages.length && <TodayRow />}
      </div>
    )
  }

  const pts = wavePoints(stages)
  const canvasW = Math.max(MARGIN * 2, MARGIN * 2 + (stages.length - 1) * SPACING)
  const todayX = tf != null ? (tf < pts.length ? pts[tf].x - SPACING / 2 : (pts.length ? pts[pts.length - 1].x + SPACING / 2 : MARGIN)) : null

  return (
    <div className="jmap border border-line overflow-x-auto overflow-y-auto" ref={scrollRef} style={{ maxHeight: '70vh' }}>
      <div className="relative" style={{ width: canvasW, height: CANVAS_H }}>
        <div className="jgrid absolute inset-0" aria-hidden="true" />
        <svg className="absolute inset-0" width={canvasW} height={CANVAS_H} aria-hidden="true">
          {pts.slice(0, -1).map((_, i) => {
            const st = segStroke(stages[i + 1].status)
            return <path key={i} d={segPath(pts, i)} fill="none" stroke={st.stroke} strokeWidth={st.width} strokeDasharray={st.dash} />
          })}
        </svg>
        {todayX != null && (
          <div className="jtoday" style={{ left: todayX }} aria-hidden="true">
            <span className="lbl" style={{ position: 'sticky', top: 2, background: 'var(--bg)', padding: '0 2px' }}>TODAY</span>
          </div>
        )}
        {stages.map((s, i) => {
          const x = pts[i].x
          const y = pts[i].y
          const above = i % 2 === 0
          const cardStyle = above
            ? { left: x - NODE_W / 2, width: NODE_W, bottom: CANVAS_H - (PATH_Y - WAVE - CONN) }
            : { left: x - NODE_W / 2, width: NODE_W, top: PATH_Y + WAVE + CONN }
          const connTop = above ? PATH_Y - WAVE - CONN : PATH_Y + WAVE
          return (
            <div key={s.id}>
              <div className="jconn absolute" style={{ left: x, top: connTop, height: CONN }} aria-hidden="true" />
              <div className={`jdot jdot-${String(s.status).toLowerCase()} absolute`} style={{ left: x - 6, top: y - 6 }} aria-hidden="true" />
              <div className="absolute" style={cardStyle}>
                <JourneyNode stage={s} selected={selectedId === s.id} dim={dim(s)}
                  onSelect={onSelect} onOpenEvidence={onOpenEvidence} onOpenParticipants={onOpenParticipants} onOpenEvidenceGroup={onOpenEvidenceGroup} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TodayRow() {
  return (
    <div className="flex items-center gap-2 my-1" aria-hidden="true">
      <span className="lbl">TODAY</span>
      <div className="flex-1" style={{ borderTop: '1px dashed var(--fg)' }} />
    </div>
  )
}

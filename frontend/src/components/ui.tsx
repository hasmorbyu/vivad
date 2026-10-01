import type { ReactNode } from 'react'
import { CLS_UI, TRUST_UI, type Cls, type TrustLabel } from '../types'

export function ClassTag({ cls, full }: { cls: Cls; full?: boolean }) {
  const u = CLS_UI[cls]
  return (
    <span className={`tag ${u.className}`}>
      {u.sym} {u.label}{full ? ` · ${u.full}` : ''}
    </span>
  )
}

export function TrustTag({ label }: { label: TrustLabel }) {
  const u = TRUST_UI[label]
  return <span className={`trust ${u.className}`}>{u.text}</span>
}

const CLAIM_STYLE: Record<string, string> = {
  SUPPORTED: 'tag-verified',
  PARTIALLY_SUPPORTED: 'tag-direct',
  CONTRADICTED: 'tag-lead',
  UNSUPPORTED: 'tag-unresolved',
  UNRESOLVED: 'tag-unresolved',
  REQUIRES_HUMAN_REVIEW: 'tag-lead',
}

export function ClaimTag({ status }: { status: string }) {
  return <span className={`tag ${CLAIM_STYLE[status] || 'tag-unresolved'}`}>{status.replaceAll('_', ' ')}</span>
}

export function Section({ title, right, children }: { title: string; right?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-6">
      <div className="flex items-end justify-between border-b border-line pb-1 mb-2">
        <h2 className="text-[13px] tracking-[.16em] uppercase">{title}</h2>
        <div className="flex gap-2">{right}</div>
      </div>
      {children}
    </section>
  )
}

export function Field({ k, children }: { k: string; children: ReactNode }) {
  return (
    <div className="mb-2">
      <div className="lbl">{k}</div>
      <div>{children}</div>
    </div>
  )
}

export function Bar({ pct }: { pct: number }) {
  return <div className="bar w-full"><i style={{ width: `${pct}%` }} /></div>
}

export function StepState({ s }: { s: string }) {
  if (s === 'OK' || s === 'DONE') return <span>[OK]</span>
  if (s === 'PROCESSING' || s === 'RUNNING') return <span className="blink">[PROCESSING]</span>
  if (s === 'ERROR') return <span style={{ fontWeight: 700 }}>[ERROR]</span>
  if (s === 'SKIPPED' || s === 'UNAVAILABLE' || s === 'WARN') return <span>[{s}]</span>
  return <span className="text-mut">[WAITING]</span>
}

export function AiUnavailable({ reason }: { reason?: string }) {
  return (
    <div className="border border-line p-2" style={{ borderStyle: 'dashed' }}>
      <div style={{ fontWeight: 700 }}>AI UNAVAILABLE</div>
      <div className="mt-1">Deterministic analysis continues normally.</div>
      {reason && <div className="lbl mt-2">REASON · {reason}</div>}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="border border-soft p-4 text-mut">{children}</div>
}

export function ErrorBanner({ message, onClose }: { message: string; onClose?: () => void }) {
  if (!message) return null
  return (
    <div role="alert" className="border border-line p-2 mb-3 flex justify-between gap-2" style={{ borderStyle: 'dashed' }}>
      <span>{message}</span>
      {onClose && <button className="btn" onClick={onClose} aria-label="dismiss error">×</button>}
    </div>
  )
}

export function Loading({ what = 'LOADING' }: { what?: string }) {
  return <div className="text-mut blink">{what}…</div>
}

import type { ReactNode } from 'react'
import { CLS_UI, TRUST_UI, type Cls, type TrustLabel } from '../types'
import { ICONS, claimVariant, classificationVariant, trustVariant, type Variant } from '../lib/semantics'

export function StatusChip({ variant = 'mut', solid, dot, children }: { variant?: Variant; solid?: boolean; dot?: boolean; children: ReactNode }) {
  return (
    <span className={`status status-${variant}${solid ? ' status-solid' : ''}`}>
      {dot && <span className="dot" aria-hidden="true" />}
      {children}
    </span>
  )
}

export function Icon({ name, className = '' }: { name: keyof typeof ICONS; className?: string }) {
  return <span className={`icon ${className}`} aria-hidden="true">{ICONS[name]}</span>
}

export function Signal({ variant = 'mut', title, children, action }: { variant?: Variant; title: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className={`signal signal-${variant}`}>
      <div className="flex flex-wrap items-baseline gap-2">
        <span style={{ fontWeight: 700 }}>{title}</span>
        {action && <span className="ml-auto">{action}</span>}
      </div>
      {children && <div className="tiny quiet">{children}</div>}
    </div>
  )
}

export function Metric({ value, label, variant, icon, onClick }: { value: ReactNode; label: string; variant?: Variant; icon?: string; onClick?: () => void }) {
  const Comp: any = onClick ? 'button' : 'div'
  return (
    <Comp className={`metric${variant ? ` metric-${variant}` : ''}`} onClick={onClick} style={{ textAlign: 'left', background: 'none', border: 0, borderLeft: '1px solid var(--soft)', cursor: onClick ? 'pointer' : 'default' }}>
      <b>{value}</b>
      <span className="lbl">{icon ? `${icon} ` : ''}{label}</span>
    </Comp>
  )
}

export function Disclosure({ summary = 'Why this is shown', children }: { summary?: string; children: ReactNode }) {
  return <details className="disclosure"><summary>{summary}</summary><div className="tiny mt-1">{children}</div></details>
}

export function ClassTag({ cls, full }: { cls: Cls; full?: boolean }) {
  const u = CLS_UI[cls]
  return <StatusChip variant={classificationVariant(cls)}>{u.sym} {u.label}{full ? ` · ${u.full}` : ''}</StatusChip>
}

export function TrustTag({ label }: { label: TrustLabel }) {
  return <StatusChip variant={trustVariant(label)}>{TRUST_UI[label].text}</StatusChip>
}

const CLAIM_VARIANT = (status: string): Variant => claimVariant(status)
export function ClaimTag({ status }: { status: string }) {
  return <StatusChip variant={CLAIM_VARIANT(status)}>{status.replaceAll('_', ' ')}</StatusChip>
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
  if (s === 'OK' || s === 'DONE') return <StatusChip variant="ok">OK</StatusChip>
  if (s === 'PROCESSING' || s === 'RUNNING') return <span className="blink"><StatusChip variant="accent">PROCESSING</StatusChip></span>
  if (s === 'ERROR') return <StatusChip variant="crit">ERROR</StatusChip>
  if (s === 'SKIPPED' || s === 'UNAVAILABLE' || s === 'WARN') return <StatusChip variant="warn">{s}</StatusChip>
  return <StatusChip variant="mut">WAITING</StatusChip>
}

export function AiUnavailable({ reason }: { reason?: string }) {
  return (
    <div className="signal signal-warn">
      <div style={{ fontWeight: 700 }}>AI UNAVAILABLE</div>
      <div className="tiny">Deterministic analysis continues normally.</div>
      {reason && <div className="lbl mt-1">REASON · {reason}</div>}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="panel p-4 quiet">{children}</div>
}

export function ErrorBanner({ message, onClose }: { message: string; onClose?: () => void }) {
  if (!message) return null
  return (
    <div role="alert" className="signal signal-crit flex justify-between gap-2">
      <span>{message}</span>
      {onClose && <button className="btn btn-quiet" onClick={onClose} aria-label="dismiss error">×</button>}
    </div>
  )
}

export function Loading({ what = 'LOADING' }: { what?: string }) {
  return <div className="quiet blink">{what}…</div>
}

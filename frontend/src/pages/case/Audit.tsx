import { useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Loading, Section, TrustTag } from '../../components/ui'
import type { J } from '../../types'

export default function Audit() {
  const { caseData } = useCase()
  const [events, setEvents] = useState<J[] | null>(null)
  const [integrity, setIntegrity] = useState<J>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get(`/cases/${caseData.id}/audit`).then(setEvents).catch((e) => setErr((e as Error).message))
    api.get(`/cases/${caseData.id}/integrity`).then(setIntegrity).catch(() => undefined)
  }, [caseData.id])

  const ok = integrity?.status === 'VERIFIED'
  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title="Integrity verification" right={integrity && <TrustTag label={ok ? 'EVIDENCE' : 'VERIFY'} />}>
        {!integrity ? <Loading /> : (
          <div className="border p-3" style={{ borderStyle: ok ? 'solid' : 'dashed', borderColor: 'var(--line)', fontWeight: ok ? 700 : 400 }}>
            <div style={{ fontSize: '15px' }}>{ok ? 'INTEGRITY VERIFIED' : 'INTEGRITY WARNING'}</div>
            <div className="grid gap-3 sm:grid-cols-3 mt-2 text-[12px]">
              <div>AUDIT CHAIN · {integrity.audit_chain.ok ? `OK (${integrity.audit_chain.events} events)` : `BROKEN AT ${integrity.audit_chain.broken_at}`}</div>
              <div>LEDGER CHAIN · {integrity.integrity_chain.ok ? `OK (${integrity.integrity_chain.records} records)` : `BROKEN AT ${integrity.integrity_chain.broken_at}`}</div>
              <div>EVIDENCE · {integrity.evidence.verified}/{integrity.evidence.total} match{integrity.evidence.mismatch.length ? ` · MISMATCH: ${integrity.evidence.mismatch.join(', ')}` : ''}</div>
            </div>
            <div className="lbl mt-2">ANCHOR · {integrity.anchor.status} · {integrity.anchor.note}</div>
            <div className="lbl mt-1">{integrity.note}</div>
          </div>
        )}
      </Section>

      <Section title={`Audit trail · ${events?.length ?? 0} events`}>
        {events === null ? <Loading /> : events.length === 0 ? <Empty>No audit events.</Empty> : (
          <div className="overflow-auto">
            <table className="tbl">
              <thead><tr><th>Seq</th><th>Action</th><th>Role</th><th>Object</th><th>From → To</th><th>When</th><th>Record hash</th></tr></thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.seq}>
                    <td>{e.seq}</td>
                    <td>{e.action}</td>
                    <td>{fmt.label(e.actor_role)}</td>
                    <td>{e.object_type}:{e.object_id}</td>
                    <td>{e.prev_state ? `${e.prev_state} → ` : ''}{e.new_state}</td>
                    <td className="whitespace-nowrap">{fmt.time(e.created_at)}</td>
                    <td><span className="mono-hash" title={e.record_hash}>{fmt.hash(e.record_hash)}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
      <div className="lbl">EACH EVENT LINKS TO THE ONE BEFORE IT BY HASH. REMOVING OR CHANGING A ROW BREAKS THE CHAIN AND IS DETECTED.</div>
    </div>
  )
}

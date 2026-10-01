import { useCallback, useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useAuth } from '../../lib/auth'
import { Empty, ErrorBanner, Field, Loading, Section, TrustTag } from '../../components/ui'
import type { J } from '../../types'

const ROLES = ['CHAIR', 'ADMIN']

export default function Decision() {
  const { caseData, reload } = useCase()
  const { user } = useAuth()
  const [existing, setExisting] = useState<J>(null)
  const [meta, setMeta] = useState<J>(null)
  const [evidence, setEvidence] = useState<J[]>([])
  const [legal, setLegal] = useState<J[]>([])
  const [reviews, setReviews] = useState<J>(null)
  const [form, setForm] = useState({ status: 'PRELIMINARY_RESOLUTION_ACCEPTED', decision: '', reason: '', observations: '', evidence_ids: [] as string[], legal_refs: [] as string[] })
  const [loaded, setLoaded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const cid = caseData.id
  const canDecide = user && ROLES.includes(user.role)

  const load = useCallback(() => {
    Promise.all([api.get(`/cases/${cid}/decision`), api.get(`/cases/${cid}/evidence`), api.get(`/cases/${cid}/legal`), api.get(`/cases/${cid}/reviews`)])
      .then(([d, e, l, r]) => { setExisting(d); setEvidence(e); setLegal(l); setReviews(r) })
      .catch((e) => setErr((e as Error).message)).finally(() => setLoaded(true))
  }, [cid])
  useEffect(() => { load(); api.get('/meta').then(setMeta).catch(() => undefined) }, [load])

  const toggle = (key: 'evidence_ids' | 'legal_refs', value: string) =>
    setForm((f) => ({ ...f, [key]: f[key].includes(value) ? f[key].filter((x) => x !== value) : [...f[key], value] }))

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr('')
    try { await api.post(`/cases/${cid}/decision`, form); load(); reload() }
    catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  if (!loaded) return <Loading what="LOADING DECISION" />
  const accepted = (reviews?.findings || []).filter((f: J) => ['ACCEPT', 'EDIT'].includes(f.human_status))
  const rejected = (reviews?.findings || []).filter((f: J) => ['REJECT', 'MARK_UNRESOLVED'].includes(f.human_status))

  return (
    <div className="max-w-[900px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      {existing ? (
        <Section title="Human decision" right={<TrustTag label="HUMAN" />}>
          <div className="border border-line p-4">
            <Field k="Decision">{existing.decision}</Field>
            <Field k="Status">{fmt.label(existing.status)}</Field>
            <Field k="Reason">{existing.reason}</Field>
            <Field k="Evidence considered">{existing.evidence_ids.join(', ') || '—'}</Field>
            <Field k="Legal references consulted">{existing.legal_refs.join(', ') || '—'}</Field>
            <Field k="AI findings accepted">{existing.accepted_finding_ids.join(', ') || '—'}</Field>
            <Field k="AI findings rejected">{existing.rejected_finding_ids.join(', ') || '—'}</Field>
            <Field k="Observations">{existing.observations || '—'}</Field>
            <div className="lbl">DECIDED BY USER {existing.decided_by} · {fmt.time(existing.decided_at)} · HUMAN-VALIDATED</div>
          </div>
        </Section>
      ) : (
        <>
          <Section title="Review status">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="border border-line p-3"><div className="lbl">AI findings accepted</div><div>{accepted.length}</div></div>
              <div className="border border-line p-3"><div className="lbl">AI findings rejected / unresolved</div><div>{rejected.length}</div></div>
            </div>
          </Section>
          <Section title="Record the human decision">
            {!canDecide && <div className="border border-line p-2 mb-3" style={{ borderStyle: 'dashed' }}>Only a chair or administrator may record the final decision.</div>}
            <p className="text-mut mb-3">This is a preliminary, non-binding resolution recorded by a human. AI never makes this decision.</p>
            <form onSubmit={submit}>
              <Field k="Outcome">
                <select className="w-full" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} aria-label="decision status" disabled={!canDecide}>
                  {(meta?.decision_statuses || []).map((d: J) => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </Field>
              <Field k="Decision"><textarea value={form.decision} onChange={(e) => setForm({ ...form, decision: e.target.value })} disabled={!canDecide} /></Field>
              <Field k="Reason"><textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} disabled={!canDecide} /></Field>
              <Field k="Evidence considered">
                <div className="flex flex-wrap gap-x-3">
                  {evidence.map((e) => <label key={e.id} className="cursor-pointer"><input type="checkbox" checked={form.evidence_ids.includes(e.evidence_ref)} onChange={() => toggle('evidence_ids', e.evidence_ref)} disabled={!canDecide} /> {e.evidence_ref}</label>)}
                </div>
              </Field>
              <Field k="Legal references consulted">
                <div className="flex flex-wrap gap-x-3">
                  {legal.map((l) => <label key={l.id} className="cursor-pointer"><input type="checkbox" checked={form.legal_refs.includes(l.legal_reference_id)} onChange={() => toggle('legal_refs', l.legal_reference_id)} disabled={!canDecide} /> {l.act} s.{l.section}</label>)}
                </div>
              </Field>
              <Field k="Observations"><textarea value={form.observations} onChange={(e) => setForm({ ...form, observations: e.target.value })} disabled={!canDecide} /></Field>
              <button className="btn" disabled={!canDecide || busy || !form.decision.trim() || !form.reason.trim()}>{busy ? 'RECORDING…' : '[ RECORD DECISION ]'}</button>
            </form>
          </Section>
        </>
      )}
      {!existing && accepted.length === 0 && <Empty>No findings have been reviewed yet. Review AI findings before recording a decision.</Empty>}
    </div>
  )
}

import { useCallback, useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Field, Loading, Section } from '../../components/ui'
import type { J } from '../../types'

const EMPTY = { party_id: '', kind: 'INITIAL', what: '', when_text: '', where_text: '', who: '', claim: '', evidence_support: '', desired_resolution: '' }

export default function Statements() {
  const { caseData } = useCase()
  const [parties, setParties] = useState<J[]>([])
  const [rows, setRows] = useState<J[]>([])
  const [form, setForm] = useState({ ...EMPTY })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    api.get(`/cases/${caseData.id}/statements`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [caseData.id])
  useEffect(() => { load(); api.get(`/cases/${caseData.id}/parties`).then(setParties).catch(() => undefined) }, [load, caseData.id])

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      await api.post(`/cases/${caseData.id}/statements`, { ...form, party_id: form.party_id ? Number(form.party_id) : null })
      setForm({ ...EMPTY, party_id: form.party_id, kind: form.kind })
      load()
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="max-w-[900px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title="Record a statement">
        <p className="text-mut mb-3">Plain language is fine. Use the fields below so VIVAD can structure the statement; you do not need legal wording.</p>
        <form onSubmit={add}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field k="Party">
              <select className="w-full" value={form.party_id} onChange={(e) => set('party_id', e.target.value)} aria-label="statement party">
                <option value="">UNASSIGNED</option>
                {parties.map((p) => <option key={p.id} value={p.id}>{p.name} ({fmt.label(p.role)})</option>)}
              </select>
            </Field>
            <Field k="Statement type">
              <select className="w-full" value={form.kind} onChange={(e) => set('kind', e.target.value)} aria-label="statement kind">
                {['INITIAL', 'RESPONSE', 'CLARIFICATION', 'SUPPLEMENTARY'].map((k) => <option key={k} value={k}>{fmt.label(k)}</option>)}
              </select>
            </Field>
          </div>
          <Field k="What happened"><textarea value={form.what} onChange={(e) => set('what', e.target.value)} /></Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field k="When did it happen"><input className="w-full" value={form.when_text} onChange={(e) => set('when_text', e.target.value)} placeholder="e.g. 14 Sep 2026" /></Field>
            <Field k="Where"><input className="w-full" value={form.where_text} onChange={(e) => set('where_text', e.target.value)} /></Field>
            <Field k="Who was involved"><input className="w-full" value={form.who} onChange={(e) => set('who', e.target.value)} /></Field>
          </div>
          <Field k="What is claimed"><textarea value={form.claim} onChange={(e) => set('claim', e.target.value)} /></Field>
          <Field k="What evidence supports this claim"><textarea value={form.evidence_support} onChange={(e) => set('evidence_support', e.target.value)} /></Field>
          <Field k="Desired resolution"><textarea value={form.desired_resolution} onChange={(e) => set('desired_resolution', e.target.value)} /></Field>
          <button className="btn" disabled={busy || (!form.claim && !form.what)}>{busy ? 'SUBMITTING…' : '[ SUBMIT STATEMENT ]'}</button>
        </form>
      </Section>
      <Section title={`Statements · ${rows.length}`}>
        {!rows ? <Loading /> : rows.length === 0 ? <Empty>No statements recorded yet.</Empty> : (
          <div className="grid gap-3">
            {rows.map((s) => (
              <article key={s.id} className="border border-soft p-3">
                <div className="lbl">{s.party_name || 'UNASSIGNED'} · {fmt.label(s.kind)} · {fmt.time(s.submitted_at)}</div>
                {s.claim && <p style={{ fontWeight: 700 }}>{s.claim}</p>}
                {s.what && <p>{s.what}</p>}
                <div className="grid gap-3 sm:grid-cols-3 text-[12px] text-mut">
                  {s.when_text && <div>WHEN · {s.when_text}</div>}
                  {s.where_text && <div>WHERE · {s.where_text}</div>}
                  {s.who && <div>WHO · {s.who}</div>}
                </div>
                {s.evidence_support && <div className="text-[12px] mt-1">SUPPORT · {s.evidence_support}</div>}
                {s.desired_resolution && <div className="text-[12px]">SEEKS · {s.desired_resolution}</div>}
              </article>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}

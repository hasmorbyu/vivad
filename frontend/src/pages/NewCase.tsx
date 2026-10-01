import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApp } from '../lib/store'
import { ErrorBanner, Field, Section } from '../components/ui'
import type { J } from '../types'

export default function NewCase() {
  const nav = useNavigate()
  const { bump } = useApp()
  const [meta, setMeta] = useState<J>(null)
  const [form, setForm] = useState({
    category: 'RENTAL_DISPUTE', title: '', description: '', location: '', incident_date: '',
    amount: '', requested_resolution: '', urgency: 'NORMAL', priority: 'NORMAL',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { api.get('/meta').then(setMeta).catch(() => undefined) }, [])

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))
  const category = meta?.categories?.find((c: J) => c.value === form.category)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      const created = await api.post('/cases', { ...form, amount: Number(form.amount || 0) })
      bump()
      nav(`/cases/${created.id}`)
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  return (
    <div className="max-w-[760px]">
      <div className="border-b border-line pb-1 mb-3">
        <h2 className="text-[13px] tracking-[.16em] uppercase">Create dispute</h2>
      </div>
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <form onSubmit={submit}>
        <Section title="1 · Dispute type">
          <Field k="Category">
            <select className="w-full" value={form.category} onChange={(e) => set('category', e.target.value)} aria-label="dispute category">
              {(meta?.categories || []).map((c: J) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>
          {category?.escalation && (
            <div className="border border-line p-2" style={{ borderStyle: 'dashed' }}>
              <div style={{ fontWeight: 700 }}>POSSIBLE ESCALATION</div>
              <div className="mt-1">Disputes of this type may need to be referred to the appropriate authority. VIVAD can still record the intake and organise evidence, but will not attempt to resolve it here.</div>
            </div>
          )}
        </Section>

        <Section title="2 · Case information">
          <Field k="Title"><input className="w-full" required value={form.title} onChange={(e) => set('title', e.target.value)} placeholder="e.g. Security deposit deduction dispute" /></Field>
          <Field k="Description"><textarea value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="Brief factual description in plain language." /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field k="Location"><input className="w-full" value={form.location} onChange={(e) => set('location', e.target.value)} /></Field>
            <Field k="Date of incident (optional)"><input className="w-full" type="date" value={form.incident_date} onChange={(e) => set('incident_date', e.target.value)} /></Field>
            <Field k="Amount involved"><input className="w-full" inputMode="numeric" value={form.amount} onChange={(e) => set('amount', e.target.value.replace(/[^\d.]/g, ''))} placeholder="0" /></Field>
            <Field k="Urgency">
              <select className="w-full" value={form.urgency} onChange={(e) => set('urgency', e.target.value)} aria-label="urgency">
                {(meta?.urgency || []).map((u: string) => <option key={u} value={u}>{u}</option>)}
              </select>
            </Field>
          </div>
          <Field k="Requested resolution"><textarea value={form.requested_resolution} onChange={(e) => set('requested_resolution', e.target.value)} placeholder="What outcome is being sought?" /></Field>
        </Section>

        <div className="flex gap-2">
          <button className="btn" type="submit" disabled={busy || !form.title}>{busy ? 'CREATING…' : '[ CREATE DISPUTE ]'}</button>
          <button className="btn" type="button" onClick={() => nav(-1)}>[ CANCEL ]</button>
        </div>
      </form>
    </div>
  )
}

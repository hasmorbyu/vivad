import { useCallback, useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Field, Loading, Section } from '../../components/ui'
import type { J } from '../../types'

export default function Parties() {
  const { caseData } = useCase()
  const [parties, setParties] = useState<J[]>([])
  const [meta, setMeta] = useState<J>(null)
  const [form, setForm] = useState({ name: '', role: 'COMPLAINANT', contact: '', relationship: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    api.get(`/cases/${caseData.id}/parties`).then(setParties).catch((e) => setErr((e as Error).message))
  }, [caseData.id])
  useEffect(() => { load(); api.get('/meta').then(setMeta).catch(() => undefined) }, [load])

  async function add(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setErr('')
    try {
      await api.post(`/cases/${caseData.id}/parties`, form)
      setForm({ name: '', role: form.role, contact: '', relationship: '' })
      load()
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }

  async function remove(id: number) {
    if (!confirm('Remove this party?')) return
    try { await api.del(`/cases/${caseData.id}/parties/${id}`); load() } catch (x) { setErr((x as Error).message) }
  }

  return (
    <div className="max-w-[900px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title="Add party">
        <form onSubmit={add}>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field k="Full name"><input className="w-full" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field k="Role">
              <select className="w-full" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} aria-label="party role">
                {(meta?.party_roles || ['COMPLAINANT', 'RESPONDENT', 'WITNESS', 'OTHER']).map((r: string) => <option key={r} value={r}>{fmt.label(r)}</option>)}
              </select>
            </Field>
            <Field k="Contact (optional)"><input className="w-full" value={form.contact} onChange={(e) => setForm({ ...form, contact: e.target.value })} /></Field>
            <Field k="Relationship to dispute"><input className="w-full" value={form.relationship} onChange={(e) => setForm({ ...form, relationship: e.target.value })} /></Field>
          </div>
          <button className="btn" disabled={busy || !form.name}>{busy ? 'ADDING…' : '[ ADD PARTY ]'}</button>
        </form>
      </Section>
      <Section title={`Parties · ${parties.length}`}>
        {!parties ? <Loading /> : parties.length === 0 ? <Empty>No parties yet. Add the complainant and respondent.</Empty> : (
          <table className="tbl"><thead><tr><th>Name</th><th>Role</th><th>Contact</th><th>Relationship</th><th /></tr></thead>
            <tbody>
              {parties.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td><td>{fmt.label(p.role)}</td><td>{p.contact || '—'}</td><td>{p.relationship || '—'}</td>
                  <td><button className="btn" onClick={() => remove(p.id)}>[ REMOVE ]</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  )
}

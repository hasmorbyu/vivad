import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useAuth } from '../../lib/auth'
import { Empty, ErrorBanner, Field, Loading, Section } from '../../components/ui'
import type { J } from '../../types'

const STAFF = ['CASE_OFFICER', 'REVIEWER', 'CHAIR', 'ADMIN']

export default function Hearings() {
  const { caseData } = useCase()
  const { user } = useAuth()
  const [rows, setRows] = useState<J[] | null>(null)
  const [form, setForm] = useState({ scheduled_at: '', duration_min: 30, agenda: '' })
  const [err, setErr] = useState('')
  const cid = caseData.id
  const canSchedule = user && STAFF.includes(user.role)

  const load = useCallback(() => {
    api.get(`/cases/${cid}/hearings`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [cid])
  useEffect(() => { load() }, [load])

  async function schedule(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    try {
      await api.post(`/cases/${cid}/hearings`, { ...form, scheduled_at: form.scheduled_at })
      setForm({ scheduled_at: '', duration_min: 30, agenda: '' })
      load()
    } catch (x) { setErr((x as Error).message) }
  }

  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      {canSchedule && (
        <Section title="Schedule a hearing">
          <form onSubmit={schedule}>
            <div className="grid gap-4 sm:grid-cols-3">
              <Field k="Date and time (IST)"><input className="w-full" type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} required /></Field>
              <Field k="Duration (minutes)"><input className="w-full" type="number" min={10} max={240} value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: Number(e.target.value) })} /></Field>
            </div>
            <Field k="Agenda"><textarea value={form.agenda} onChange={(e) => setForm({ ...form, agenda: e.target.value })} /></Field>
            <button className="btn" disabled={!form.scheduled_at}>[ SCHEDULE HEARING ]</button>
            <div className="lbl mt-2">PARTICIPANTS DEFAULT TO THE PARTIES. INVITATIONS APPEAR IN-APP.</div>
          </form>
        </Section>
      )}
      <Section title={`Hearings · ${rows?.length ?? 0}`}>
        {rows === null ? <Loading /> : rows.length === 0 ? <Empty>No hearings scheduled.</Empty> : (
          <div className="grid gap-3">
            {rows.map((h) => (
              <article key={h.id} className="border border-line p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span style={{ fontWeight: 700 }}>{h.scheduled_at ? fmt.time(h.scheduled_at) : 'UNSCHEDULED'}</span>
                  <span className="lbl">{h.duration_min} MIN · {h.status}</span>
                  <span className="lbl ml-auto">{h.provider} · {h.room_id}</span>
                </div>
                {h.agenda && <p className="my-1">{h.agenda}</p>}
                <div className="lbl">Participants</div>
                <div className="flex flex-wrap gap-x-3 mb-2">
                  {h.participants.map((p: J) => <span key={p.id}>{p.name} <span className="text-mut">({fmt.label(p.role)})</span>{p.attended ? ' ✓' : ''}</span>)}
                </div>
                <Link className="btn no-underline" to={`/hearings/${h.id}`}>[ OPEN HEARING ]</Link>
              </article>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}

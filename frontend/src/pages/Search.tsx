import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { Empty, ErrorBanner, Section } from '../components/ui'
import type { J } from '../types'

export default function Search() {
  const [params] = useSearchParams()
  const q = params.get('q') || ''
  const [data, setData] = useState<J>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (q.trim().length < 2) { setData(null); return }
    setBusy(true); setErr('')
    api.get(`/search?q=${encodeURIComponent(q)}`).then(setData).catch((e) => setErr((e as Error).message)).finally(() => setBusy(false))
  }, [q])

  const r = data?.results
  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Search · “${q}”${busy ? ' …' : ''}`}>
        {q.trim().length < 2 && <Empty>Type at least two characters in the search box above.</Empty>}
        {data && r.total === 0 && <Empty>No matches for “{q}”.</Empty>}
        {data && r.total > 0 && (
          <div className="grid gap-4">
            {r.cases.length > 0 && <Group title="Cases">
              {r.cases.map((c: J) => <Link key={c.id} className="link" to={`/cases/${c.id}`}>{c.id} · {c.title} <span className="text-mut">({c.status})</span></Link>)}
            </Group>}
            {r.parties.length > 0 && <Group title="Parties">
              {r.parties.map((p: J, i: number) => <Link key={i} className="link" to={`/cases/${p.case_id}/parties`}>{p.name} · {p.role}</Link>)}
            </Group>}
            {r.evidence.length > 0 && <Group title="Evidence">
              {r.evidence.map((e: J) => <Link key={e.id} className="link" to={`/cases/${e.case_id}/evidence/${e.id}`}>[{e.evidence_ref}] {e.filename} · {e.status}</Link>)}
            </Group>}
            {r.claims.length > 0 && <Group title="Claims">
              {r.claims.map((c: J, i: number) => <Link key={i} className="link" to={`/cases/${c.case_id}/claims`}>{c.claim_ref} · {c.text} <span className="text-mut">({c.status})</span></Link>)}
            </Group>}
            {r.events.length > 0 && <Group title="Timeline events">
              {r.events.map((e: J, i: number) => <Link key={i} className="link" to={`/cases/${e.case_id}/timeline`}>{e.event_ref} · {e.title}</Link>)}
            </Group>}
            {r.hearings.length > 0 && <Group title="Hearings">
              {r.hearings.map((h: J) => <Link key={h.id} className="link" to={`/hearings/${h.id}`}>{h.scheduled_at || 'unscheduled'} · {h.agenda || h.status}</Link>)}
            </Group>}
            {r.legal.length > 0 && <Group title="Legal references (dataset)">
              {r.legal.map((l: J) => <span key={l.id}>{l.act} s.{l.section} · {l.title}</span>)}
            </Group>}
          </div>
        )}
      </Section>
    </div>
  )
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="lbl mb-1">{title}</div>
      <div className="grid gap-1">{children}</div>
    </div>
  )
}

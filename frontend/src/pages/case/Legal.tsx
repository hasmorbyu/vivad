import { useEffect, useMemo, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Loading, Section, TrustTag } from '../../components/ui'
import type { J } from '../../types'

export default function Legal() {
  const { caseData } = useCase()
  const [rows, setRows] = useState<J[] | null>(null)
  const [q, setQ] = useState('')
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get(`/cases/${caseData.id}/legal`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [caseData.id])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (rows || []).filter((r) => !needle || [r.act, r.section, r.title, r.description, (r.concepts || []).join(' ')]
      .join(' ').toLowerCase().includes(needle))
  }, [rows, q])

  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Relevant legal references · ${filtered.length}`} right={<TrustTag label="VERIFY" />}>
        <p className="text-mut mb-3">Reference material for authorised human review only. VIVAD does not interpret the law, determine liability, or give legal advice. Always verify against the official source.</p>
        <input className="w-full mb-3" placeholder="SEARCH ACT, SECTION, TITLE OR CONCEPT" value={q} onChange={(e) => setQ(e.target.value)} aria-label="search legal references" />
        {rows === null ? <Loading /> : filtered.length === 0 ? <Empty>No references associated{rows.length ? ' matching your search' : ''}. Run analysis to associate legal references.</Empty> : (
          <div className="grid gap-4">
            {filtered.map((r) => (
              <article key={r.id} className="border border-line p-3">
                <div className="lbl">{r.act} · SECTION {r.section}</div>
                <h3 className="text-[14px]">{r.title}</h3>
                <p className="my-2">{r.description}</p>
                <div className="border border-soft p-2 mb-2">
                  <div className="lbl">Why this is shown</div>
                  <div>{r.relevance}</div>
                  {r.concepts.length > 0 && <div className="lbl mt-1">Detected concepts · {r.concepts.join(', ')}</div>}
                </div>
                <div className="grid gap-3 sm:grid-cols-3 text-[12px] text-mut">
                  <div>JURISDICTION · {r.jurisdiction}</div>
                  <div>LAST VERIFIED · {r.last_verified ? fmt.date(r.last_verified) : '—'}</div>
                  <div>STATUS · {r.status.replaceAll('_', ' ')}</div>
                </div>
                <div className="flex gap-2 mt-2">
                  <a className="btn no-underline" href={r.source_url} target="_blank" rel="noreferrer">[ VIEW SOURCE ]</a>
                </div>
                {r.disclaimer && <div className="lbl mt-2">{r.disclaimer}</div>}
              </article>
            ))}
          </div>
        )}
      </Section>
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Disclosure, Empty, ErrorBanner, Loading, Section } from '../../components/ui'
import type { J } from '../../types'

export default function Legal() {
  const { caseData } = useCase()
  const [rows, setRows] = useState<J[] | null>(null)
  const [claims, setClaims] = useState<J[]>([])
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState<J | null>(null)
  const [err, setErr] = useState('')
  const cid = caseData.id

  useEffect(() => {
    api.get(`/cases/${cid}/legal`).then(setRows).catch((e) => setErr((e as Error).message))
    api.get(`/cases/${cid}/claims`).then(setClaims).catch(() => undefined)
  }, [cid])

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return (rows || []).filter((r) => !needle || [r.act, r.section, r.title, (r.concepts || []).join(' ')]
      .join(' ').toLowerCase().includes(needle))
  }, [rows, q])

  function connections(ref: J) {
    const words = (ref.concepts || []).map((c: string) => c.toLowerCase())
    return claims.map((c) => {
      const text = (c.text || '').toLowerCase()
      const hits = words.filter((w: string) => text.includes(w))
      return hits.length ? { claim: c, hits } : null
    }).filter(Boolean) as { claim: J; hits: string[] }[]
  }

  return (
    <div className="max-w-[1100px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Legal references · ${filtered.length}`}>
        <div className="tiny quiet mb-2">Reference material for authorised human review only. VIVAD does not interpret the law or give legal advice. Verify against the official source.</div>
        <input className="w-full mb-3 max-w-[420px]" placeholder="SEARCH ACT, SECTION OR CONCEPT" value={q} onChange={(e) => setQ(e.target.value)} aria-label="search legal references" />
        {rows === null ? <Loading /> : filtered.length === 0 ? <Empty>No references associated yet.</Empty> : (
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="min-w-0">
              {filtered.map((r) => (
                <button key={r.id} onClick={() => setSelected(r)}
                  className="block w-full text-left border-b border-soft py-3 hover:bg-sub"
                  style={selected?.id === r.id ? { background: 'var(--sub2)' } : undefined}>
                  <div className="flex items-baseline gap-3">
                    <span className="display" style={{ fontSize: 20 }}>§{r.section}</span>
                    <span style={{ fontWeight: 700 }}>{r.act}</span>
                    <span className="ml-auto lbl">{r.status.replaceAll('_', ' ')}</span>
                  </div>
                  <div className="mt-1">{r.title}</div>
                  <div className="flex flex-wrap gap-x-2 gap-y-1 mt-1">
                    {r.concepts.slice(0, 6).map((c: string, i: number) => (
                      <span key={i} className="tiny quiet" style={{ borderBottom: '1px dotted var(--soft)' }}>{c}</span>
                    ))}
                  </div>
                </button>
              ))}
            </div>

            <aside className="lg:sticky lg:top-2 self-start">
              {!selected ? (
                <Empty>Select a reference to see why VIVAD surfaced it and how it connects to the case.</Empty>
              ) : (
                <div className="border border-line p-3">
                  <div className="display" style={{ fontSize: 24 }}>§{selected.section}</div>
                  <div style={{ fontWeight: 700 }}>{selected.act}</div>
                  <div className="mb-2">{selected.title}</div>
                  <p className="tiny">{selected.description}</p>
                  <hr className="hair" />
                  <div className="lbl mb-1">Why VIVAD surfaced this</div>
                  <div className="flex flex-wrap gap-1 mb-1">
                    {selected.concepts.map((c: string, i: number) => <span key={i} className="jchip">{c}</span>)}
                  </div>
                  <Disclosure summary="Full explanation">{selected.relevance}</Disclosure>

                  <ConnectionList ref_={selected} claims={connections(selected)} />

                  <div className="flex gap-2 mt-2">
                    <a className="btn no-underline" href={selected.source_url} target="_blank" rel="noreferrer">[ VIEW SOURCE ]</a>
                  </div>
                  <div className="lbl mt-2">{selected.jurisdiction} · last verified {selected.last_verified ? fmt.date(selected.last_verified) : '—'}</div>
                  <Disclosure summary="Disclaimer">
                    {selected.disclaimer}
                  </Disclosure>
                </div>
              )}
            </aside>
          </div>
        )}
      </Section>
    </div>
  )
}

function ConnectionList({ ref_, claims }: { ref_: J; claims: { claim: J; hits: string[] }[] }) {
  if (claims.length === 0) return null
  return (
    <>
      <hr className="hair" />
      <div className="lbl mb-1">Case connections</div>
      {claims.slice(0, 4).map(({ claim, hits }) => (
        <div key={claim.id} className="tiny mb-1">
          <span style={{ fontWeight: 700 }}>{claim.claim_ref}</span> · {claim.text.slice(0, 70)}
          <div className="quiet">matched · {hits.join(', ')}</div>
          {claim.evidence?.length > 0 && (
            <div className="quiet">evidence · {claim.evidence.map((e: J) => e.evidence_ref).join(', ')}</div>
          )}
        </div>
      ))}
      <div className="tiny quiet">§{ref_.section} ← claims ← evidence, shown for orientation only.</div>
    </>
  )
}

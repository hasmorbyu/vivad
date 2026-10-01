import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useAuth } from '../../lib/auth'
import { Empty, Field, Loading, Section, StepState, TrustTag } from '../../components/ui'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

export default function CaseOverview() {
  const { caseData } = useCase()
  const { user } = useAuth()
  const cid = caseData.id
  const [claims, setClaims] = useState<J[]>([])
  const [contradictions, setContradictions] = useState<J[]>([])
  const [legal, setLegal] = useState<J[]>([])
  const [analysis, setAnalysis] = useState<J>(null)
  const [status, setStatus] = useState<J>(null)
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState('')

  const loadData = useCallback(() => {
    Promise.all([
      api.get(`/cases/${cid}/claims`), api.get(`/cases/${cid}/contradictions`),
      api.get(`/cases/${cid}/legal`), api.get(`/cases/${cid}/analysis`),
    ]).then(([cl, c, l, a]) => { setClaims(cl); setContradictions(c); setLegal(l); setAnalysis(a) })
      .catch((e) => setErr((e as Error).message)).finally(() => setLoaded(true))
  }, [cid])
  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    api.get(`/cases/${cid}/analyze/status`).then((s) => { if (s.steps && s.state !== 'NOT_RUN') setStatus(s) }).catch(() => undefined)
  }, [cid])
  useEffect(() => {
    if (status?.state !== 'RUNNING') return
    const t = setInterval(async () => {
      const s = await api.get(`/cases/${cid}/analyze/status`).catch(() => null)
      if (!s) return
      setStatus(s)
      if (s.state !== 'RUNNING') { clearInterval(t); loadData() }
    }, 600)
    return () => clearInterval(t)
  }, [status?.state, cid, loadData])

  const canAnalyse = user && user.role !== 'RESPONDENT'
  const running = status?.state === 'RUNNING'
  const done = caseData.analysis_state === 'DONE' || analysis?.status
  const out = analysis?.analysis || {}
  const summary = caseData.summary_text || out.summary
  const source = caseData.summary_source || (analysis?.provider ? `AI:${analysis.provider}` : null)

  async function run() {
    setErr('')
    try { setStatus(await api.post(`/cases/${cid}/analyze`)) } catch (e) { setErr((e as Error).message) }
  }

  return (
    <div className="max-w-[1000px]">
      {err && <div className="border border-line p-2 mb-3" style={{ borderStyle: 'dashed', fontWeight: 700 }}>{err}</div>}

      <Section title="Status" right={
        canAnalyse && !running ? <button className="btn" onClick={run}>{done ? '[ RE-RUN ANALYSIS ]' : '[ RUN ANALYSIS ]'}</button> : undefined}>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field k="Status">{fmt.label(caseData.status)}</Field>
          <Field k="Stage">{fmt.label(caseData.current_stage)}</Field>
          <Field k="Next action">{caseData.next_action}</Field>
        </div>
        {status?.steps && status.state !== 'NOT_RUN' && (
          <div className="mt-2">
            {status.steps.map((s: J) => (
              <div key={s.name} className="grid grid-cols-[minmax(200px,280px)_120px_1fr] gap-2 border-b border-soft py-[2px]">
                <span>{s.name}</span><StepState s={s.status} /><span className="text-mut text-[12px]">{s.detail}</span>
              </div>
            ))}
            {running && <div className="blink mt-1">ANALYSIS RUNNING…</div>}
          </div>
        )}
        {!done && !running && <p className="text-mut mt-2">Run analysis to extract claims, link evidence, build the timeline, flag potential contradictions and associate legal references.</p>}
      </Section>

      <Section title="AI case summary" right={source ? <TrustTag label={source.startsWith('AI') ? 'AI' : 'EVIDENCE'} /> : undefined}>
        {!loaded ? <Loading /> : summary ? (
          <div className="border border-line p-4 whitespace-pre-wrap">{summary}
            <div className="lbl mt-2">SOURCE · {source}{analysis?.validation ? ` · ${analysis.validation}` : ''}</div>
          </div>
        ) : <Empty>No case summary yet. Run analysis.</Empty>}
      </Section>

      <Section title="Key issues">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="border border-line p-3"><div className="text-[20px]">{fmt.n(caseData.stats.claims)}</div><div className="lbl mt-1">Claims</div></div>
          <div className="border border-line p-3"><div className="text-[20px]">{fmt.n(contradictions.length)}</div><div className="lbl mt-1">Potential contradictions</div></div>
          <div className="border border-line p-3"><div className="text-[20px]">{fmt.n(legal.length)}</div><div className="lbl mt-1">Relevant legal references</div></div>
        </div>
        {out.missing_information?.length > 0 && (
          <div className="mt-3">
            <div className="lbl mb-1">Missing information</div>
            <ul className="list-none pl-0">
              {out.missing_information.slice(0, 6).map((m: J, i: number) => <li key={i}>· {m.text}</li>)}
            </ul>
          </div>
        )}
      </Section>

      <Section title="Claims and evidence references" right={<Link className="btn no-underline" to="claims">[ ALL CLAIMS ]</Link>}>
        {!loaded ? <Loading /> : claims.length === 0 ? <Empty>No claims yet.</Empty> : (
          <div className="grid gap-2">
            {claims.slice(0, 8).map((c) => (
              <div key={c.id} className="border border-soft p-2">
                <div className="lbl">{c.claim_ref} · {c.party_name || 'PARTY'} · {c.status.replaceAll('_', ' ')}</div>
                <div>{c.text} {c.amount ? <b>{fmt.money(c.amount)}</b> : null}</div>
                <div className="flex flex-wrap gap-x-2 mt-1">
                  {c.evidence.map((e: J, i: number) => <EvidenceRef key={i} caseId={cid} id={e.id} ref_={e.evidence_ref} />)}
                  {c.evidence.length === 0 && <span className="lbl">NO EVIDENCE LINKED</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Potential contradictions" right={<Link className="btn no-underline" to="contradictions">[ REVIEW ]</Link>}>
        {!loaded ? <Loading /> : contradictions.length === 0 ? <Empty>None flagged.</Empty> : (
          <div className="grid gap-2">
            {contradictions.slice(0, 4).map((c) => (
              <div key={c.id} className="border border-soft p-2">
                <div className="lbl">{c.contradiction_ref} · {c.kind_label} · {c.verification_status.replaceAll('_', ' ')}</div>
                <div style={{ fontWeight: 700 }}>{c.title}</div>
                <div className="text-[12px]">{c.explanation}</div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Relevant legal references" right={<Link className="btn no-underline" to="legal">[ VIEW ALL ]</Link>}>
        {!loaded ? <Loading /> : legal.length === 0 ? <Empty>No references associated yet.</Empty> : (
          <div className="grid gap-2">
            {legal.slice(0, 3).map((l) => (
              <div key={l.id} className="border border-soft p-2">
                <div className="lbl">{l.act} · SECTION {l.section}</div>
                <div>{l.title}</div>
                <div className="text-[12px] text-mut">{l.relevance}</div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="lbl">AI-ASSISTED MATERIAL IS LABELLED THROUGHOUT. HUMAN-VALIDATED MATERIAL IS LABELLED SEPARATELY. VIVAD ISSUES NO DECISION.</div>
    </div>
  )
}

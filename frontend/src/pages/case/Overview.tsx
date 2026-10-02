import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useAuth } from '../../lib/auth'
import { ClaimTag, Disclosure, Loading, Metric, Section, Signal, StatusChip } from '../../components/ui'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

export default function CaseOverview() {
  const { caseData } = useCase()
  const { user } = useAuth()
  const nav = useNavigate()
  const cid = caseData.id
  const [journey, setJourney] = useState<J>(null)
  const [claims, setClaims] = useState<J[]>([])
  const [contradictions, setContradictions] = useState<J[]>([])
  const [legal, setLegal] = useState<J[]>([])
  const [findings, setFindings] = useState<J[]>([])
  const [loaded, setLoaded] = useState(false)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    Promise.all([
      api.get(`/cases/${cid}/journey`), api.get(`/cases/${cid}/claims`), api.get(`/cases/${cid}/contradictions`),
      api.get(`/cases/${cid}/legal`), api.get(`/cases/${cid}/reviews`),
    ]).then(([j, cl, co, le, rv]) => { setJourney(j); setClaims(cl); setContradictions(co); setLegal(le); setFindings(rv.findings || []) })
      .catch((e) => setErr((e as Error).message)).finally(() => setLoaded(true))
  }, [cid])
  useEffect(() => { load() }, [load])

  const s = caseData.stats
  const analysed = caseData.analysis_state === 'DONE'
  const canAct = user && user.role !== 'RESPONDENT'
  const openContra = contradictions.filter((c) => c.verification_status === 'REQUIRES_HUMAN_REVIEW').length
  const pendingFindings = findings.filter((f) => f.human_status === 'PENDING').length
  const supportedClaims = claims.filter((c) => c.status === 'SUPPORTED').length

  async function runAnalysis() {
    setErr('')
    try { await api.post(`/cases/${cid}/analyze`) ; nav(`/cases/${cid}/review`) } catch (e) { setErr((e as Error).message) }
  }

  // One obvious primary action, in the order a case officer would act.
  let primary: { label: string; to?: string; onClick?: () => void } | null = null
  if (!analysed && canAct) primary = { label: 'RUN ANALYSIS', onClick: runAnalysis }
  else if (s.decisions > 0) primary = { label: 'VIEW REPORT', to: `/cases/${cid}/report` }
  else if (caseData.status === 'AWAITING_DECISION' && canAct) primary = { label: 'RECORD DECISION', to: `/cases/${cid}/decision` }
  else if (pendingFindings > 0 && canAct) primary = { label: 'REVIEW FINDINGS', to: `/cases/${cid}/review` }
  else primary = { label: 'OPEN CASE', to: `/cases/${cid}/evidence` }

  const priorityFindings = [...findings].sort((a, b) => {
    const rank = (f: J) => (f.human_status === 'PENDING' ? 0 : f.kind === 'CONTRADICTION' ? 1 : 2)
    return rank(a) - rank(b)
  }).slice(0, 4)

  return (
    <div className="max-w-[1100px]">
      {err && <div className="signal signal-crit">{err}</div>}
      {!loaded ? <Loading what="LOADING CASE" /> : (
        <>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            {primary && (
              primary.onClick
                ? <button className="btn btn-primary" onClick={primary.onClick}>[ {primary.label} ]</button>
                : <Link className="btn btn-primary no-underline" to={primary.to!}>[ {primary.label} ]</Link>
            )}
            <span className="lbl ml-auto">{fmt.label(caseData.current_stage)}</span>
          </div>

          <Section title="At a glance">
            <div className="flex flex-wrap border border-line">
              <Metric value={fmt.n(s.parties)} label="Parties" />
              <Metric value={fmt.n(s.evidence)} label="Evidence" icon="▣" />
              <Metric value={fmt.n(contradictions.length)} label="Contradictions" icon="⚠" variant={openContra > 0 ? 'crit' : undefined} onClick={() => nav(`/cases/${cid}/contradictions`)} />
              <Metric value={fmt.n(legal.length)} label="Legal refs" icon="§" onClick={() => nav(`/cases/${cid}/legal`)} />
              <Metric value={fmt.n(s.claims)} label="Claims" icon="⚑" onClick={() => nav(`/cases/${cid}/claims`)} />
              <Metric value={fmt.n(s.events)} label="Timeline events" icon="⌁" onClick={() => nav(`/cases/${cid}/timeline`)} />
            </div>
          </Section>

          <Section title="Case signals">
            {openContra > 0 && (
              <Signal variant="crit" title={`⚠ ${openContra} contradiction${openContra > 1 ? 's' : ''} require review`}
                action={<Link className="btn no-underline" to={`/cases/${cid}/contradictions`}>[ REVIEW ]</Link>}>
                Inconsistencies between statements and evidence. A potential contradiction is not a finding of wrongdoing.
              </Signal>
            )}
            {journey?.stages?.some((st: J) => st.kind === 'HEARING' && st.flag === 'CRITICAL') && (
              <Signal variant="crit" title="! A scheduled hearing is overdue" action={<Link className="btn no-underline" to={`/cases/${cid}/hearings`}>[ HEARINGS ]</Link>}>
                The scheduled time has passed and the hearing is not marked complete.
              </Signal>
            )}
            {journey?.stages?.some((st: J) => st.kind === 'EVIDENCE_SUBMITTED' && st.flag === 'CRITICAL') && (
              <Signal variant="crit" title="▣ Evidence integrity warning" action={<Link className="btn no-underline" to={`/cases/${cid}/audit`}>[ AUDIT ]</Link>}>
                A stored file no longer matches the SHA-256 recorded at intake.
              </Signal>
            )}
            {!analysed && (
              <Signal variant="warn" title="Case not analysed yet">Run analysis to extract claims, link evidence and flag contradictions.</Signal>
            )}
            <Signal variant="ok" title={`▣ ${s.evidence} evidence item${s.evidence === 1 ? '' : 's'} · ${s.evidence_verified} integrity-verified`} />
            <Signal variant="ok" title={`${supportedClaims} of ${claims.length} claim${claims.length === 1 ? '' : 's'} have documentary support`} />
            <Signal variant="mut" title={`${s.parties} parties · ${s.statements} statements · ${legal.length} legal references`} />
          </Section>

          <Section title="Case timeline" right={<Link className="btn btn-quiet no-underline" to={`/cases/${cid}/timeline`}>[ OPEN JOURNEY ]</Link>}>
            {journey?.stages?.length ? <MiniTimeline stages={journey.stages} caseId={cid} /> : <div className="quiet tiny">No stages yet.</div>}
          </Section>

          <Section title="Key findings" right={<Link className="btn btn-quiet no-underline" to={`/cases/${cid}/review`}>[ ALL FINDINGS ]</Link>}>
            {priorityFindings.length === 0 ? <div className="quiet">No findings yet.</div> : (
              <div>
                {priorityFindings.map((f: J) => (
                  <div key={f.id} className="border-b border-soft py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="lbl">{f.finding_ref}</span>
                      <StatusChip variant={f.origin === 'AI' ? 'warn' : 'mut'}>{f.origin}</StatusChip>
                      <StatusChip variant={f.human_status === 'PENDING' ? 'warn' : 'ok'}>{f.human_status}</StatusChip>
                    </div>
                    <div style={{ fontWeight: 700 }}>{f.title}</div>
                    <div className="tiny">{f.body}</div>
                    {f.evidence?.length > 0 && (
                      <div className="flex flex-wrap gap-x-2 mt-1">{f.evidence.map((e: J, i: number) => <EvidenceRef key={i} caseId={cid} id={e.id} ref_={e.evidence_ref} />)}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Claims and evidence">
            {claims.length === 0 ? <div className="quiet">No claims yet.</div> : (
              <div>
                {claims.slice(0, 5).map((c) => (
                  <div key={c.id} className="border-b border-soft py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="lbl">{c.claim_ref} · {c.party_name || 'PARTY'}</span>
                      <ClaimTag status={c.status} />
                    </div>
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

          <Section title="About this case">
            {caseData.description && <div className="mb-2">{caseData.description}</div>}
            {caseData.requested_resolution && <div className="tiny quiet mb-2">Requested resolution · {caseData.requested_resolution}</div>}
            <Disclosure summary="How VIVAD works on this case">
              AI assists analysis; deterministic code links evidence; a human makes every decision. Shared identifiers and
              graph paths are not proof. SHA-256 verifies integrity, not chain of custody. Legal references are reference
              material only and VIVAD does not interpret the law.
            </Disclosure>
          </Section>
        </>
      )}
    </div>
  )
}

function MiniTimeline({ stages, caseId }: { stages: J[]; caseId: string }) {
  return (
    <div className="flex items-center gap-0 overflow-x-auto pb-1">
      {stages.map((st: J, i: number) => {
        const colour = st.status === 'COMPLETED' ? 'var(--ok)' : st.status === 'CURRENT' ? 'var(--accent)' : 'var(--soft)'
        return (
          <div key={st.id} className="flex items-center">
            {i > 0 && <div style={{ width: 34, borderTop: `1px solid ${st.status === 'UPCOMING' ? 'var(--soft)' : 'var(--fg)'}` }} />}
            <Link to={`/cases/${caseId}/timeline`} className="no-underline" style={{ color: 'inherit' }} title={st.title}>
              <div className="flex flex-col items-center" style={{ minWidth: 78 }}>
                <span style={{ display: 'inline-block', width: 12, height: 12, background: colour, border: '2px solid ' + colour }} />
                <span className="tiny quiet mt-1 text-center" style={{ lineHeight: 1.2 }}>{st.date ? fmt.date(st.date) : '—'}</span>
                <span className="tiny text-center" style={{ maxWidth: 100, lineHeight: 1.2 }}>{st.title}</span>
              </div>
            </Link>
          </div>
        )
      })}
    </div>
  )
}

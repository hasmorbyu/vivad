import { useCallback, useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useAuth } from '../../lib/auth'
import { Empty, ErrorBanner, Loading, Section, TrustTag } from '../../components/ui'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

const KIND_LABEL: Record<string, string> = {
  FACT_SUPPORTED: 'Fact supported by evidence',
  CLAIM_REQUIRING_VERIFICATION: 'Claim requiring verification',
  CONTRADICTION: 'Potential contradiction',
  MISSING_INFORMATION: 'Missing information',
  RESOLUTION_PATH: 'Possible next step',
  HEARING_QUESTION: 'Question for the hearing',
}
const STAFF = ['CASE_OFFICER', 'REVIEWER', 'CHAIR', 'ADMIN']

export default function Review() {
  const { caseData } = useCase()
  const { user } = useAuth()
  const [data, setData] = useState<J>(null)
  const [requests, setRequests] = useState<J[]>([])
  const [editing, setEditing] = useState<{ id: number; text: string } | null>(null)
  const [req, setReq] = useState({ about: '', party_id: '' })
  const [err, setErr] = useState('')
  const cid = caseData.id
  const canReview = user && STAFF.includes(user.role)

  const load = useCallback(() => {
    api.get(`/cases/${cid}/reviews`).then(setData).catch((e) => setErr((e as Error).message))
    api.get(`/cases/${cid}/evidence-requests`).then(setRequests).catch(() => undefined)
  }, [cid])
  useEffect(() => { load() }, [load])

  async function act(findingId: number, action: string, extra: J = {}) {
    setErr('')
    try { await api.post(`/cases/${cid}/reviews`, { finding_id: findingId, action, ...extra }); setEditing(null); load() }
    catch (e) { setErr((e as Error).message) }
  }
  async function submitRequest(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.post(`/cases/${cid}/evidence-requests`, { about: req.about, party_id: req.party_id ? Number(req.party_id) : null })
      setReq({ about: '', party_id: '' }); load()
    } catch (x) { setErr((x as Error).message) }
  }

  if (!data) return <Loading what="LOADING FINDINGS" />
  const findings: J[] = data.findings
  const pending = findings.filter((f) => f.human_status === 'PENDING')

  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Human review · ${findings.length} findings · ${pending.length} pending`}>
        <p className="text-mut mb-3">Every AI finding must be reviewed by a human. Accept, reject, edit or mark unresolved; the action is recorded with your name and the time. AI never makes a decision.</p>
        {!canReview && <div className="border border-line p-2 mb-3" style={{ borderStyle: 'dashed' }}>Your role can view findings but not action them.</div>}
        {findings.length === 0 && <Empty>No findings. Run analysis first.</Empty>}
        <div className="grid gap-3">
          {findings.map((f) => (
            <article key={f.id} className="border border-line p-3">
              <div className="flex flex-wrap items-center gap-2 border-b border-soft pb-1 mb-2">
                <span style={{ fontWeight: 700 }}>{f.finding_ref}</span>
                <span className="lbl">{KIND_LABEL[f.kind] || f.kind}</span>
                <TrustTag label={f.origin === 'AI' ? 'AI' : 'EVIDENCE'} />
                {f.human_status !== 'PENDING' ? <TrustTag label="HUMAN" /> : <TrustTag label="VERIFY" />}
                <span className="lbl ml-auto">{f.human_status.replaceAll('_', ' ')}</span>
              </div>
              <div style={{ fontWeight: 700 }}>{f.title}</div>
              {editing !== null && editing.id === f.id ? (
                <div className="my-2">
                  <textarea value={editing.text} onChange={(e) => setEditing({ id: f.id, text: e.target.value })} />
                  <button className="btn mt-1" onClick={() => act(f.id, 'EDIT', { edited_body: editing.text })}>[ SAVE EDIT ]</button>
                </div>
              ) : <p className="my-1">{f.body}</p>}
              {f.evidence?.length > 0 && (
                <div className="flex flex-wrap gap-x-2 mb-1">
                  {f.evidence.map((e: J, i: number) => <EvidenceRef key={i} caseId={cid} id={e.id} ref_={e.evidence_ref} />)}
                </div>
              )}
              {f.validation && <div className="lbl">VALIDATION · {f.validation}</div>}
              {canReview && (
                <div className="flex flex-wrap gap-2 mt-2">
                  <button className="btn" onClick={() => act(f.id, 'ACCEPT')} disabled={!canReview && f.kind === 'HEARING_QUESTION'}>[ ACCEPT ]</button>
                  <button className="btn" onClick={() => act(f.id, 'REJECT')}>[ REJECT ]</button>
                  <button className="btn" onClick={() => setEditing({ id: f.id, text: f.body })}>[ EDIT ]</button>
                  <button className="btn" onClick={() => act(f.id, 'REQUEST_EVIDENCE')}>[ REQUEST EVIDENCE ]</button>
                  <button className="btn" onClick={() => act(f.id, 'MARK_UNRESOLVED')}>[ MARK UNRESOLVED ]</button>
                </div>
              )}
            </article>
          ))}
        </div>
      </Section>

      <Section title={`Evidence requests · ${requests.length}`}>
        {canReview && (
          <form className="border border-soft p-3 mb-3" onSubmit={submitRequest}>
            <label className="lbl block mb-1" htmlFor="req-about">What is needed</label>
            <input id="req-about" className="w-full mb-2" value={req.about} onChange={(e) => setReq({ ...req, about: e.target.value })} placeholder="e.g. Please provide the repair invoice." />
            <button className="btn" disabled={!req.about.trim()}>[ SEND REQUEST ]</button>
          </form>
        )}
        {requests.length === 0 ? <Empty>No evidence requests.</Empty> : (
          <table className="tbl"><thead><tr><th>About</th><th>Party</th><th>Status</th><th>Raised</th></tr></thead>
            <tbody>{requests.map((r) => <tr key={r.id}><td>{r.about}</td><td>{r.party_name || '—'}</td><td>{r.status}</td><td>{fmt.time(r.created_at)}</td></tr>)}</tbody>
          </table>
        )}
      </Section>

      {data.history.length > 0 && (
        <Section title="Review history">
          <table className="tbl"><thead><tr><th>Finding</th><th>Action</th><th>Reviewer</th><th>When</th><th>Comment</th></tr></thead>
            <tbody>{data.history.map((h: J) => (
              <tr key={h.id}><td>{h.finding_id}</td><td>{h.action.replaceAll('_', ' ')}</td>
                <td>{h.reviewer_name} ({fmt.label(h.reviewer_role)})</td><td>{fmt.time(h.created_at)}</td><td>{h.comment || '—'}</td></tr>
            ))}</tbody>
          </table>
        </Section>
      )}
    </div>
  )
}

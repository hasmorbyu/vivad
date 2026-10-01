import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Field, Loading, Section, TrustTag } from '../../components/ui'
import type { J } from '../../types'

const IMG = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp']
const PDF = ['pdf']

export default function EvidenceDetail() {
  const { evidenceId } = useParams<{ evidenceId: string }>()
  const { caseData } = useCase()
  const [d, setD] = useState<J>(null)
  const [lines, setLines] = useState<J>(null)
  const [verify, setVerify] = useState<J>(null)
  const [err, setErr] = useState('')

  const load = useCallback(() => {
    api.get(`/cases/${caseData.id}/evidence/${evidenceId}`).then(setD).catch((e) => setErr((e as Error).message))
  }, [caseData.id, evidenceId])
  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!d) return
    const ext = (d.media_type || '').toLowerCase()
    if (!PDF.includes(ext) && !IMG.includes(ext)) {
      api.get(`/cases/${caseData.id}/evidence/${evidenceId}/lines?count=400`).then(setLines).catch(() => undefined)
    }
  }, [d, caseData.id, evidenceId])

  if (err) return <Empty>{err}</Empty>
  if (!d) return <Loading what="LOADING EVIDENCE" />
  const ext = (d.media_type || '').toLowerCase()
  const fileUrl = `/api/cases/${caseData.id}/evidence/${evidenceId}/file`

  async function runVerify() {
    try { setVerify(await api.get(`/cases/${caseData.id}/evidence/${evidenceId}/verify`)) } catch (e) { setErr((e as Error).message) }
  }

  return (
    <div className="max-w-[1100px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <div className="flex flex-wrap items-center gap-3 border-b border-line pb-1 mb-3">
        <h2 className="text-[14px] tracking-[.14em]">EVIDENCE {d.evidence_ref}</h2>
        <TrustTag label="EVIDENCE" />
        <Link className="btn no-underline ml-auto" to="..">[ BACK TO EVIDENCE ]</Link>
        <button className="btn" onClick={runVerify}>[ VERIFY INTEGRITY ]</button>
      </div>
      {verify && (
        <div className="border border-line p-2 mb-3" style={{ borderStyle: verify.integrity === 'VERIFIED' ? 'solid' : 'dashed', fontWeight: verify.integrity === 'VERIFIED' ? 700 : 400 }}>
          {verify.integrity === 'VERIFIED' ? 'INTEGRITY VERIFIED' : 'INTEGRITY WARNING'} — {verify.integrity === 'VERIFIED'
            ? 'the stored file still matches the SHA-256 recorded at intake.'
            : verify.reason}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          <Section title="Preview">
            {IMG.includes(ext) ? <img src={fileUrl} alt={d.filename} className="max-w-full border border-line" /> :
              PDF.includes(ext) ? <iframe src={fileUrl} title={d.filename} className="w-full border border-line" style={{ height: '60vh' }} /> :
              lines && lines.file.previewable ? (
                <div className="border border-line overflow-auto" style={{ maxHeight: '50vh' }}>
                  {lines.lines.map((l: J) => (
                    <div key={l.n} className="grid grid-cols-[64px_1fr]">
                      <span className="px-2 text-right border-r border-soft text-mut">{String(l.n).padStart(4, '0')} │</span>
                      <span className="px-2 whitespace-pre-wrap break-all">{l.text || ' '}{l.ref && <span className="lbl ml-2">{l.ref}</span>}</span>
                    </div>
                  ))}
                </div>
              ) : <Empty>Preview not available for this file type. The original file is preserved unchanged.</Empty>}
          </Section>

          <Section title="Extracted information" right={<TrustTag label="EVIDENCE" />}>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field k={`Amounts (${d.extracted.amounts.length})`}>
                {d.extracted.amounts.length === 0 ? <span className="text-mut">none detected</span> :
                  <div className="flex flex-wrap gap-2">{d.extracted.amounts.map((a: number, i: number) => <span key={i}>{fmt.money(a)}</span>)}</div>}
              </Field>
              <Field k={`Dates (${d.extracted.dates.length})`}>
                {d.extracted.dates.length === 0 ? <span className="text-mut">none detected</span> :
                  <div className="flex flex-wrap gap-2">{d.extracted.dates.map((x: J, i: number) => <span key={i}>{fmt.date(x.iso)}</span>)}</div>}
              </Field>
            </div>
            <Field k={`Entities (${d.extracted.entities.length})`}>
              {d.extracted.entities.length === 0 ? <span className="text-mut">none detected</span> : (
                <div className="max-h-56 overflow-auto border border-soft">
                  {d.extracted.entities.slice(0, 120).map((e: J, i: number) => (
                    <div key={i} className="border-b border-soft px-1"><span className="lbl">{e.type}</span> {e.value}</div>
                  ))}
                </div>
              )}
            </Field>
          </Section>
        </div>

        <div className="min-w-0">
          <Section title="Metadata">
            <Field k="File">{d.filename}</Field>
            <Field k="Type">{d.source_type} · {d.media_type || '—'}</Field>
            <Field k="Size">{fmt.size(d.file_size)}</Field>
            <Field k="Uploaded">{fmt.time(d.uploaded_at)}</Field>
            <Field k="Description">{d.description || <span className="text-mut">—</span>}</Field>
            <Field k="SHA-256"><span className="mono-hash">{d.sha256}</span></Field>
            <Field k="Verification">{d.verify_status || 'NOT CHECKED'}</Field>
          </Section>

          <Section title="Related">
            <Field k={`Claims (${d.related_claims.length})`}>
              {d.related_claims.length === 0 ? <span className="text-mut">none linked</span> :
                d.related_claims.map((c: J, i: number) => <div key={i}>{c.claim_ref} · {c.relationship}<div className="text-mut text-[12px]">{c.text}</div></div>)}
            </Field>
            <Field k="Party">{d.related_party ? `${d.related_party.name} (${fmt.label(d.related_party.role)})` : <span className="text-mut">—</span>}</Field>
            <Field k={`Events (${d.related_events.length})`}>
              {d.related_events.length === 0 ? <span className="text-mut">none</span> : d.related_events.map((e: J, i: number) => <div key={i}>{e.event_ref} · {e.title}</div>)}
            </Field>
            <Field k={`Contradictions (${d.related_contradictions.length})`}>
              {d.related_contradictions.length === 0 ? <span className="text-mut">none</span> : d.related_contradictions.map((c: J, i: number) => <div key={i}>{c.contradiction_ref} · {c.title}</div>)}
            </Field>
            <Field k={`Related evidence (${d.related_evidence.length})`}>
              {d.related_evidence.length === 0 ? <span className="text-mut">none</span> : d.related_evidence.map((e: J, i: number) => <div key={i}>{e.evidence_ref} · {e.filename}</div>)}
            </Field>
          </Section>

          <Section title="Audit history">
            {d.audit_history.length === 0 ? <span className="text-mut">no events</span> : (
              <div className="border border-soft">
                {d.audit_history.map((h: J, i: number) => (
                  <div key={i} className="border-b border-soft p-1 text-[12px]">
                    <div><b>{h.action}</b> · {h.new_state}</div>
                    <div className="text-mut">{fmt.time(h.created_at)} · {h.actor_role}</div>
                  </div>
                ))}
              </div>
            )}
            {d.integrity.length > 0 && (
              <div className="mt-2">
                <div className="lbl">Integrity record</div>
                <div className="mono-hash">{d.integrity[0].object_hash}</div>
                <div className="lbl mt-1">{d.integrity[0].anchor_status}</div>
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  )
}

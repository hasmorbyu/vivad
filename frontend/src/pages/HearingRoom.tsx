import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { useAuth } from '../lib/auth'
import { Empty, ErrorBanner, Field, Loading, Section, TrustTag } from '../components/ui'
import type { J } from '../types'

const STAFF = ['CASE_OFFICER', 'REVIEWER', 'CHAIR', 'ADMIN']
const CONTEXT_TABS = ['SUMMARY', 'EVIDENCE', 'TIMELINE', 'CLAIMS', 'CONTRADICTIONS', 'LEGAL']

export default function HearingRoom() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [hearing, setHearing] = useState<J>(null)
  const [ctx, setCtx] = useState<J>({})
  const [meeting, setMeeting] = useState<J>(null)
  const [tab, setTab] = useState('SUMMARY')
  const [note, setNote] = useState({ issue: '', party_a: '', party_b: '', additional_evidence: '', next_action: '' })
  const [err, setErr] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const canStaff = user && STAFF.includes(user.role)

  const loadHearing = useCallback(() => {
    api.get(`/hearings/${id}`).then(async (h) => {
      setHearing(h)
      const cid = h.case_id
      const [caseD, analysis, claims, contra, evidence, timeline, legal] = await Promise.all([
        api.get(`/cases/${cid}`), api.get(`/cases/${cid}/analysis`), api.get(`/cases/${cid}/claims`),
        api.get(`/cases/${cid}/contradictions`), api.get(`/cases/${cid}/evidence`),
        api.get(`/cases/${cid}/timeline`), api.get(`/cases/${cid}/legal`),
      ])
      setCtx({ caseD, analysis, claims, contra, evidence, timeline, legal })
    }).catch((e) => setErr((e as Error).message))
  }, [id])
  useEffect(() => { loadHearing() }, [loadHearing])

  async function join() {
    setErr('')
    try {
      const res = await api.post(`/hearings/${id}/join`)
      setMeeting(res.meeting)
      setHearing(res.hearing)
      if (res.meeting.provider === 'local') {
        try {
          streamRef.current = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
          if (videoRef.current) videoRef.current.srcObject = streamRef.current
        } catch { setErr('Camera/microphone unavailable. You can still take notes and view case context.') }
      }
    } catch (e) { setErr((e as Error).message) }
  }
  useEffect(() => () => { streamRef.current?.getTracks().forEach((t) => t.stop()) }, [])

  async function saveNote(e: React.FormEvent) {
    e.preventDefault()
    try { await api.post(`/hearings/${id}/notes`, note); setNote({ issue: '', party_a: '', party_b: '', additional_evidence: '', next_action: '' }); loadHearing() }
    catch (x) { setErr((x as Error).message) }
  }
  async function complete() {
    try { await api.patch(`/hearings/${id}`, { status: 'COMPLETED' }); loadHearing() } catch (e) { setErr((e as Error).message) }
  }

  if (!hearing) return <div className="p-4"><Loading what="LOADING HEARING" /></div>
  const cid = hearing.case_id

  return (
    <div className="max-w-[1200px]">
      <div className="flex flex-wrap items-center gap-2 border-b border-line pb-1 mb-3">
        <h2 className="text-[14px] tracking-[.14em]">HEARING {hearing.id}</h2>
        <span className="lbl">{hearing.scheduled_at ? fmt.time(hearing.scheduled_at) : 'UNSCHEDULED'} · {hearing.status}</span>
        <Link className="btn no-underline ml-auto" to={`/cases/${cid}/hearings`}>[ ALL HEARINGS ]</Link>
        {canStaff && hearing.status !== 'COMPLETED' && <button className="btn" onClick={complete}>[ MARK COMPLETED ]</button>}
      </div>
      <ErrorBanner message={err} onClose={() => setErr('')} />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="min-w-0">
          <Section title="Video hearing">
            {!meeting ? (
              <Empty>
                <p className="mb-2">Join the hearing room. Recording is off by default and is not started automatically.</p>
                <button className="btn" onClick={join}>[ JOIN HEARING ]</button>
              </Empty>
            ) : meeting.url ? (
              <iframe title="hearing" src={meeting.url} className="w-full border border-line" style={{ height: '52vh' }}
                allow="camera; microphone; fullscreen; display-capture; autoplay" />
            ) : (
              <div className="border border-line p-2">
                <video ref={videoRef} autoPlay muted playsInline className="w-full bg-black" style={{ maxHeight: '44vh' }} />
                <div className="lbl mt-1">LOCAL OFFLINE ROOM · NO REMOTE PEERS · CAMERA/MIC PREVIEW ONLY</div>
              </div>
            )}
            <div className="lbl mt-1">PROVIDER · {meeting?.provider || hearing.provider} · ROOM {meeting?.room_id || hearing.room_id}</div>
          </Section>

          <Section title="Participants">
            <table className="tbl"><thead><tr><th>Name</th><th>Role</th><th>Invited</th><th>Attended</th></tr></thead>
              <tbody>{hearing.participants.map((p: J) => (
                <tr key={p.id}><td>{p.name}</td><td>{fmt.label(p.role)}</td><td>{p.invited ? 'YES' : 'NO'}</td><td>{p.attended ? 'YES' : '—'}</td></tr>
              ))}</tbody>
            </table>
          </Section>

          <Section title="Hearing notes" right={<TrustTag label="HUMAN" />}>
            {canStaff && (
              <form className="border border-soft p-3 mb-3" onSubmit={saveNote}>
                {[['issue', 'Issue discussed'], ['party_a', 'Party A clarification'], ['party_b', 'Party B clarification'],
                  ['additional_evidence', 'Additional evidence requested'], ['next_action', 'Next action']].map(([k, label]) => (
                  <div key={k} className="mb-2">
                    <label className="lbl block mb-1" htmlFor={`n-${k}`}>{label}</label>
                    <textarea id={`n-${k}`} value={(note as J)[k]} onChange={(e) => setNote({ ...note, [k]: e.target.value })} />
                  </div>
                ))}
                <button className="btn">[ SAVE NOTE ]</button>
              </form>
            )}
            {hearing.notes.length === 0 ? <Empty>No notes recorded.</Empty> : hearing.notes.map((n: J) => (
              <div key={n.id} className="border border-soft p-2 mb-2">
                <div className="lbl">NOTE {n.id} · {fmt.time(n.created_at)}</div>
                {Object.entries(n.body).filter(([, v]) => v).map(([k, v]) => <div key={k}><span className="lbl">{k.replaceAll('_', ' ')}</span> · {String(v)}</div>)}
              </div>
            ))}
          </Section>
        </div>

        <aside className="min-w-0">
          <div className="flex flex-wrap gap-1 border-b border-line pb-1 mb-2">
            {CONTEXT_TABS.map((t) => <button key={t} className={'btn ' + (tab === t ? 'on' : '')} onClick={() => setTab(t)}>{t}</button>)}
          </div>
          <div className="border border-line p-3 max-h-[70vh] overflow-auto">
            {tab === 'SUMMARY' && <Summary ctx={ctx} />}
            {tab === 'EVIDENCE' && <List items={(ctx.evidence || []).map((e: J) => `[${e.evidence_ref}] ${e.filename} — ${e.status}`)} />}
            {tab === 'TIMELINE' && <Timeline items={ctx.timeline || []} />}
            {tab === 'CLAIMS' && <List items={(ctx.claims || []).map((c: J) => `${c.claim_ref} (${c.status}): ${c.text}`)} />}
            {tab === 'CONTRADICTIONS' && <List items={(ctx.contra || []).map((c: J) => `${c.contradiction_ref} — ${c.title}: ${c.explanation}`)} />}
            {tab === 'LEGAL' && <List items={(ctx.legal || []).map((l: J) => `${l.act} s.${l.section} — ${l.title}`)} />}
          </div>
        </aside>
      </div>
    </div>
  )
}

function List({ items }: { items: string[] }) {
  if (!items.length) return <Empty>Nothing recorded.</Empty>
  return <div className="grid gap-1">{items.map((t, i) => <div key={i} className="border-b border-soft py-[3px]">{t}</div>)}</div>
}
function Timeline({ items }: { items: J[] }) {
  if (!items.length) return <Empty>No events.</Empty>
  return <div className="grid gap-1">{items.map((e) => <div key={e.event_ref} className="border-b border-soft py-[3px]"><span className="lbl">{fmt.time(e.event_time)}</span> {e.title}{e.evidence_ref ? ` [${e.evidence_ref}]` : ''}</div>)}</div>
}
function Summary({ ctx }: { ctx: J }) {
  const text = ctx.caseD?.summary_text || ctx.analysis?.analysis?.summary
  return (
    <>
      <Field k="Status">{ctx.caseD ? `${fmt.label(ctx.caseD.status)} · ${fmt.label(ctx.caseD.current_stage)}` : '—'}</Field>
      <Field k="Case summary">{text || <span className="text-mut">No summary yet.</span>}</Field>
    </>
  )
}

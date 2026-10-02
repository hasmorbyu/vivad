import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { useApp } from '../lib/store'
import { ErrorBanner, Field, Section } from '../components/ui'
import type { J } from '../types'

interface IntakeFile {
  id: string
  file: File
  name: string
  size: number
  status: 'READY' | 'UPLOADING' | 'DONE' | 'ERROR'
  error?: string
}

export default function Uploads() {
  const nav = useNavigate()
  const { bump } = useApp()
  const [meta, setMeta] = useState<J>(null)
  const [tab, setTab] = useState<'NEW_CASE' | 'INSPECT_UPLOADS'>('NEW_CASE')
  const [form, setForm] = useState({
    category: 'RENTAL_DISPUTE',
    title: '',
    description: '',
    location: '',
    incident_date: '',
    amount: '',
    requested_resolution: '',
    urgency: 'NORMAL',
    priority: 'NORMAL',
  })
  const [intakeFiles, setIntakeFiles] = useState<IntakeFile[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.get('/meta').then(setMeta).catch(() => undefined)
  }, [])

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))
  const category = meta?.categories?.find((c: J) => c.value === form.category)

  function handleFileSelection(files: FileList | File[]) {
    const list = Array.from(files)
    const newEntries: IntakeFile[] = list.map((f) => ({
      id: f.name + '-' + f.size + '-' + Math.random(),
      file: f,
      name: f.name,
      size: f.size,
      status: 'READY',
    }))
    setIntakeFiles((prev) => [...prev, ...newEntries])
  }

  function removeFile(id: string) {
    setIntakeFiles((prev) => prev.filter((f) => f.id !== id))
  }

  async function submitIntake(e: React.FormEvent) {
    e.preventDefault()
    if (!form.title.trim()) return
    setBusy(true)
    setErr('')

    try {
      // Step 1: Register new case record
      const created = await api.post('/cases', { ...form, amount: Number(form.amount || 0) })
      const cid = created.id

      // Step 2: Upload all attached intake evidence documents
      for (const item of intakeFiles) {
        setIntakeFiles((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, status: 'UPLOADING' } : f))
        )
        try {
          await api.upload(cid, item.file, {}, () => {})
          setIntakeFiles((prev) =>
            prev.map((f) => (f.id === item.id ? { ...f, status: 'DONE' } : f))
          )
        } catch (uploadErr) {
          setIntakeFiles((prev) =>
            prev.map((f) =>
              f.id === item.id
                ? { ...f, status: 'ERROR', error: (uploadErr as Error).message }
                : f
            )
          )
        }
      }

      bump()
      // Step 3: Transition to the Cases section for the newly created case
      nav(`/cases/${cid}`)
    } catch (x) {
      setErr((x as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="max-w-[840px]">
      {/* Header Banner */}
      <div className="border-b border-line pb-2 mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="lbl">SECTION 03</div>
          <h1 className="title text-[18px] tracking-[.14em] uppercase">UPLOADS &amp; INTAKE</h1>
          <div className="quiet tiny">
            Register new dispute cases and upload initial intake files, contracts, and evidence.
          </div>
        </div>
        <div className="flex gap-1">
          <button
            className={`btn ${tab === 'NEW_CASE' ? 'on' : ''}`}
            onClick={() => setTab('NEW_CASE')}
          >
            [ REGISTER &amp; UPLOAD ]
          </button>
        </div>
      </div>

      <ErrorBanner message={err} onClose={() => setErr('')} />

      <form onSubmit={submitIntake}>
        {/* Step 1: Dispute Classification */}
        <Section title="1 · DISPUTE CLASSIFICATION">
          <Field k="Dispute Category">
            <select
              className="w-full"
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
              aria-label="dispute category"
            >
              {(meta?.categories || []).map((c: J) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </Field>
          {category?.escalation && (
            <div className="border border-line p-2 mt-2 bg-sub" style={{ borderStyle: 'dashed' }}>
              <div className="font-bold text-warn">POSSIBLE ESCALATION NOTICE</div>
              <div className="tiny quiet mt-0.5">
                Disputes in this category may require formal regulatory referral. VIVAD will store and index evidence, but human evaluation is mandatory.
              </div>
            </div>
          )}
        </Section>

        {/* Step 2: Case Details */}
        <Section title="2 · CASE DETAILS">
          <Field k="Case Title">
            <input
              className="w-full"
              required
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              placeholder="e.g. Rental Security Deposit Non-Refund Dispute"
            />
          </Field>
          <Field k="Detailed Description">
            <textarea
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              placeholder="Provide a clear, factual summary of the dispute in plain language."
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field k="Location / Jurisdiction">
              <input
                className="w-full"
                value={form.location}
                onChange={(e) => set('location', e.target.value)}
                placeholder="e.g. Bengaluru, Karnataka"
              />
            </Field>
            <Field k="Incident Date">
              <input
                className="w-full"
                type="date"
                value={form.incident_date}
                onChange={(e) => set('incident_date', e.target.value)}
              />
            </Field>
            <Field k="Disputed Amount (₹)">
              <input
                className="w-full"
                inputMode="numeric"
                value={form.amount}
                onChange={(e) => set('amount', e.target.value.replace(/[^\d.]/g, ''))}
                placeholder="40000"
              />
            </Field>
            <Field k="Urgency Level">
              <select
                className="w-full"
                value={form.urgency}
                onChange={(e) => set('urgency', e.target.value)}
                aria-label="urgency level"
              >
                {(meta?.urgency || ['NORMAL', 'HIGH', 'CRITICAL']).map((u: string) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field k="Requested Remedy / Outcome">
            <textarea
              value={form.requested_resolution}
              onChange={(e) => set('requested_resolution', e.target.value)}
              placeholder="What resolution or financial refund is being requested?"
            />
          </Field>
        </Section>

        {/* Step 3: Intake Document Uploads */}
        <Section title="3 · INTAKE DOCUMENTS &amp; EVIDENCE UPLOADS">
          <div className="lbl mb-2">INITIAL EVIDENCE FILES (CONTRACTS, CSV, RECEIPTS, IMAGES)</div>
          
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            multiple
            onChange={(e) => {
              if (e.target.files) handleFileSelection(e.target.files)
            }}
          />

          <div
            className="border-2 border-dashed border-soft p-6 text-center cursor-pointer hover:border-fg transition-colors bg-sub"
            onClick={() => fileInputRef.current?.click()}
          >
            <div className="text-[20px] mb-1">📁</div>
            <div className="font-bold">CLICK OR DRAG FILES TO ATTACH INTAKE DOCUMENTS</div>
            <div className="quiet tiny mt-1">
              Supports .txt, .csv, .pdf, .json, .png, .jpg files. SHA-256 integrity hashes are computed automatically on ingest.
            </div>
          </div>

          {/* Uploaded File List */}
          {intakeFiles.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="lbl">ATTACHED FILE QUEUE ({intakeFiles.length})</div>
              {intakeFiles.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between border border-soft p-2 bg-bg text-[12px]"
                >
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span>📄</span>
                    <span className="font-mono font-bold truncate">{item.name}</span>
                    <span className="quiet tiny">({(item.size / 1024).toFixed(1)} KB)</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {item.status === 'READY' && <span className="tag tag-lead">READY</span>}
                    {item.status === 'UPLOADING' && <span className="tag tag-direct blink">UPLOADING…</span>}
                    {item.status === 'DONE' && <span className="tag tag-verified">UPLOADED</span>}
                    {item.status === 'ERROR' && <span className="tag status-crit">ERROR</span>}
                    <button
                      type="button"
                      className="btn text-[10px] py-0 px-1"
                      onClick={() => removeFile(item.id)}
                      disabled={busy}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Submit Actions */}
        <div className="flex flex-wrap gap-2 mt-6 border-t border-line pt-4">
          <button
            className="btn btn-primary py-2 px-4 font-bold"
            type="submit"
            disabled={busy || !form.title.trim()}
          >
            {busy ? 'REGISTERING & INGESTING UPLOADS…' : '[ REGISTER DISPUTE & INGEST UPLOADS ]'}
          </button>
          <button
            className="btn py-2 px-4"
            type="button"
            onClick={() => nav('/cases')}
          >
            [ CANCEL ]
          </button>
        </div>
      </form>
    </div>
  )
}

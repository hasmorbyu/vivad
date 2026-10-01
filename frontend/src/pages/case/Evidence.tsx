import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { useApp } from '../../lib/store'
import { Bar, Empty, ErrorBanner, Section } from '../../components/ui'
import type { J } from '../../types'

interface Up { key: string; name: string; size: number; phase: 'UPLOADING' | 'PARSING' | 'DONE' | 'ERROR'; pct: number; error?: string }

export default function Evidence() {
  const { caseData } = useCase()
  const { bump } = useApp()
  const [files, setFiles] = useState<J[]>([])
  const [ups, setUps] = useState<Up[]>([])
  const [drag, setDrag] = useState(false)
  const [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const cid = caseData.id

  const load = useCallback(() => {
    api.get(`/cases/${cid}/evidence`).then(setFiles).catch((e) => setErr((e as Error).message))
  }, [cid])
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!files.some((f) => f.status === 'HASHED' || f.status === 'PARSING')) return
    const t = setInterval(() => { load(); bump() }, 1200)
    return () => clearInterval(t)
  }, [files, load, bump])

  async function addFiles(list: FileList | File[]) {
    const arr = Array.from(list)
    const entries: Up[] = arr.map((f) => ({ key: f.name + f.size + Math.random(), name: f.name, size: f.size, phase: 'UPLOADING', pct: 0 }))
    setUps((u) => [...entries, ...u])
    setErr('')
    for (let i = 0; i < arr.length; i++) {
      const e = entries[i]
      const patch = (p: Partial<Up>) => setUps((u) => u.map((x) => (x.key === e.key ? { ...x, ...p } : x)))
      try {
        const rec = await api.upload(cid, arr[i], {}, (pct) => patch({ pct }))
        patch({ phase: 'PARSING', pct: 100 })
        pollParse(e.key, rec.id)
      } catch (x) { patch({ phase: 'ERROR', error: (x as Error).message }) }
    }
    bump()
  }

  function pollParse(key: string, id: number) {
    const t = setInterval(async () => {
      try {
        const list: J[] = await api.get(`/cases/${cid}/evidence`)
        setFiles(list)
        const f = list.find((x) => x.id === id)
        if (f && (f.status === 'PARSED' || f.status === 'ERROR')) {
          clearInterval(t)
          setUps((u) => u.map((x) => (x.key === key ? { ...x, phase: f.status === 'PARSED' ? 'DONE' : 'ERROR', error: f.status === 'ERROR' ? f.message : undefined } : x)))
          bump()
        }
      } catch { clearInterval(t) }
    }, 800)
  }

  const pending = files.some((f) => f.status === 'HASHED' || f.status === 'PARSING')

  return (
    <div>
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title="Add evidence" right={<span className="lbl">PDF · TXT · CSV · JSON · EML · IMAGES · AUDIO · VIDEO</span>}>
        <div
          onDragOver={(e) => { e.preventDefault(); setDrag(true) }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files) }}
          className="border p-6 text-center" style={{ border: `${drag ? 2 : 1}px ${drag ? 'solid' : 'dashed'} var(--fg)` }}>
          <div className="tracking-[.12em]">DROP EVIDENCE FILES HERE</div>
          <div className="lbl my-1">Each file receives an evidence reference (E-001, E-002, …)</div>
          <button className="btn mt-2" onClick={() => input.current?.click()}>[ SELECT FILES ]</button>
          <input ref={input} type="file" multiple hidden onChange={(e) => e.target.files && addFiles(e.target.files)} />
        </div>
        {ups.length > 0 && (
          <div className="mt-3 grid gap-2">
            {ups.slice(0, 12).map((u) => (
              <div key={u.key} className="border border-soft p-2">
                <div className="flex justify-between"><span>{u.name}</span><span className="text-mut">{fmt.size(u.size)}</span></div>
                <div className="grid grid-cols-[110px_1fr_90px] gap-2 items-center mt-1">
                  <span>UPLOAD</span><Bar pct={u.pct} /><span>{u.phase === 'UPLOADING' ? `${u.pct}%` : '[OK]'}</span>
                </div>
                <div className="grid grid-cols-[110px_1fr_90px] gap-2 items-center">
                  <span>PROCESS</span>
                  <span className={u.phase === 'PARSING' ? 'blink' : ''}>
                    {u.phase === 'UPLOADING' ? 'WAITING' : u.phase === 'PARSING' ? 'PROCESSING' : u.phase === 'DONE' ? 'COMPLETE' : 'FAILED'}
                  </span>
                  <span>{u.phase === 'DONE' ? '[OK]' : u.phase === 'ERROR' ? '[ERR]' : ''}</span>
                </div>
                {u.error && <div style={{ fontWeight: 700 }}>{u.error}</div>}
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={`Evidence inventory · ${files.length} files${pending ? ' · PROCESSING' : ''}`}>
        {files.length === 0 ? <Empty>No evidence uploaded yet.</Empty> : (
          <div className="overflow-auto">
            <table className="tbl">
              <thead><tr><th>Ref</th><th>File</th><th>Type</th><th className="text-right">Records</th><th className="text-right">Size</th><th>SHA-256</th><th>Status</th></tr></thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.id} className="row">
                    <td className="whitespace-nowrap"><Link className="link" to={`${f.id}`}>[{f.evidence_ref}]</Link></td>
                    <td>{f.filename}{f.message && <div className="text-[11px] text-mut">{f.message}</div>}</td>
                    <td>{f.source_type}</td>
                    <td className="text-right">{fmt.n(f.record_count)}</td>
                    <td className="text-right">{fmt.size(f.file_size)}</td>
                    <td title={f.sha256}><span className="mono-hash">{fmt.hash(f.sha256)}</span></td>
                    <td>{f.status === 'ERROR' ? 'ERROR' : f.status !== 'PARSED' ? f.status : f.verify_status === 'VERIFIED' ? 'VERIFIED' : f.verify_status === 'MISMATCH' ? 'MISMATCH' : 'PARSED'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  )
}

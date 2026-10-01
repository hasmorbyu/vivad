import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { useApp } from '../lib/store'
import { Empty, ErrorBanner, Section } from '../components/ui'
import type { J } from '../types'

export default function Cases() {
  const { version, error, setError } = useApp()
  const nav = useNavigate()
  const [rows, setRows] = useState<J[] | null>(null)

  const load = useCallback(() => {
    api.get('/cases').then(setRows).catch((e) => setError((e as Error).message))
  }, [setError])
  useEffect(() => { load() }, [load, version])

  return (
    <div className="max-w-[1200px]">
      <ErrorBanner message={error || ''} onClose={() => setError(null)} />
      <div className="flex items-end justify-between border-b border-line pb-1 mb-3">
        <h2 className="text-[13px] tracking-[.16em] uppercase">Cases</h2>
        <Link className="btn no-underline" to="/cases/new">[ CREATE DISPUTE ]</Link>
      </div>
      <Section title={`All cases · ${rows?.length ?? 0}`}>
        {rows === null && <Empty>Loading…</Empty>}
        {rows && rows.length === 0 && <Empty>No cases. Create a dispute to begin.</Empty>}
        {rows && rows.length > 0 && (
          <div className="overflow-auto">
            <table className="tbl">
              <thead><tr><th>Case</th><th>Category</th><th>Parties</th><th>Stage</th><th>Status</th><th className="text-right">Evidence</th><th>Opened</th></tr></thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="row" onClick={() => nav(`/cases/${c.id}`)}>
                    <td style={{ fontWeight: 700 }}>{c.id}{c.synthetic ? <span className="lbl ml-2">SYNTHETIC</span> : null}</td>
                    <td>{fmt.label(c.category)}</td>
                    <td>{c.party_summary || <span className="text-mut">—</span>}</td>
                    <td>{fmt.label(c.current_stage)}</td>
                    <td>{fmt.label(c.status)}</td>
                    <td className="text-right">{fmt.n(c.stats.evidence)}</td>
                    <td className="whitespace-nowrap">{fmt.date(c.created_at)}</td>
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

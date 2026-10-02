import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, fmt } from '../lib/api'
import { useApp } from '../lib/store'
import { useAuth } from '../lib/auth'
import { Empty, ErrorBanner, Section, StatusChip } from '../components/ui'
import { caseStatusVariant } from '../lib/semantics'
import type { J } from '../types'

const METRICS: [string, string][] = [
  ['active_cases', 'Active cases'],
  ['awaiting_review', 'Awaiting review'],
  ['hearings_scheduled', 'Hearings scheduled'],
  ['evidence_pending', 'Evidence pending'],
  ['requiring_validation', 'Requiring validation'],
  ['resolved_closed', 'Resolved / closed'],
]

export default function Dashboard() {
  const { version, error, setError } = useApp()
  const { user } = useAuth()
  const nav = useNavigate()
  const [data, setData] = useState<J>(null)
  const [busy, setBusy] = useState(true)

  const load = useCallback(() => {
    setBusy(true)
    api.get('/dashboard').then(setData).catch((e) => setError((e as Error).message)).finally(() => setBusy(false))
  }, [setError])
  useEffect(() => { load() }, [load, version])

  const canCreate = user && user.role !== 'RESPONDENT'

  return (
    <div className="max-w-[1200px]">
      <ErrorBanner message={error || ''} onClose={() => setError(null)} />
      <div className="flex items-end justify-between border-b border-line pb-1 mb-3">
        <h2 className="text-[13px] tracking-[.16em] uppercase">Dashboard</h2>
        {canCreate && <Link className="btn no-underline" to="/cases/new">[ CREATE DISPUTE ]</Link>}
      </div>

      <Section title="Overview">
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3">
          {METRICS.map(([key, label]) => (
            <div key={key} className="border border-line p-3">
              <div className="text-[24px]">{data ? fmt.n(data.metrics[key]) : '--'}</div>
              <div className="lbl mt-1">{label}</div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Case queue" right={busy ? <span className="lbl blink">LOADING…</span> : undefined}>
        {!data && <Empty>No data.</Empty>}
        {data && data.cases.length === 0 && <Empty>No cases yet. Create a dispute to begin intake.</Empty>}
        {data && data.cases.length > 0 && (
          <div className="overflow-auto">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Case</th><th>Category</th><th>Parties</th><th>Status</th><th>Priority</th>
                  <th className="text-right">Evidence</th><th className="text-right">Contradictions</th>
                  <th>Next action</th><th>Opened</th>
                </tr>
              </thead>
              <tbody>
                {data.cases.map((c: J) => (
                  <tr key={c.id} className="row" onClick={() => nav(`/cases/${c.id}`)}>
                    <td className="whitespace-nowrap" style={{ fontWeight: 700 }}>{c.id}{c.synthetic ? <span className="lbl ml-2">SYNTHETIC</span> : null}</td>
                    <td>{fmt.label(c.category)}</td>
                    <td>{c.party_summary || <span className="text-mut">—</span>}</td>
                    <td className="whitespace-nowrap"><StatusChip variant={caseStatusVariant(c.status)} dot>{fmt.label(c.status)}</StatusChip></td>
                    <td>{fmt.label(c.priority)}</td>
                    <td className="text-right">{fmt.n(c.stats.evidence)}</td>
                    <td className="text-right" style={c.stats.contradictions_open > 0 ? { color: 'var(--crit)', fontWeight: 700 } : undefined}>{fmt.n(c.stats.contradictions)}</td>
                    <td>{c.next_action}</td>
                    <td className="whitespace-nowrap">{fmt.date(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <div className="lbl">STATUS AND COUNTS ARE COMPUTED BY THE BACKEND. VIVAD IS A PRELIMINARY DECISION-SUPPORT TOOL, NOT A COURT.</div>
    </div>
  )
}

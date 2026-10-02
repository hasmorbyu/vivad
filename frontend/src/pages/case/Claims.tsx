import { useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { ClaimTag, Empty, ErrorBanner, Loading, Section } from '../../components/ui'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

export default function Claims() {
  const { caseData } = useCase()
  const [rows, setRows] = useState<J[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get(`/cases/${caseData.id}/claims`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [caseData.id])

  return (
    <div className="max-w-[1100px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Claims · ${rows?.length ?? 0}`}>
        {rows === null ? <Loading /> : rows.length === 0 ? <Empty>No claims yet. Run analysis to extract claims from the statements.</Empty> : (
          <div className="overflow-auto">
            <table className="tbl">
              <thead><tr><th>Ref</th><th>Party</th><th>Claim</th><th className="text-right">Amount</th><th>Date</th><th>Status</th><th>Supporting evidence</th></tr></thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="row">
                    <td className="whitespace-nowrap">{c.claim_ref}</td>
                    <td className="whitespace-nowrap">{c.party_name || <span className="text-mut">—</span>}</td>
                    <td>{c.text}</td>
                    <td className="text-right whitespace-nowrap">{c.amount ? fmt.money(c.amount) : '—'}</td>
                    <td className="whitespace-nowrap">{c.date ? fmt.date(c.date) : '—'}</td>
                    <td className="whitespace-nowrap"><ClaimTag status={c.status} /></td>
                    <td>{c.evidence.length === 0 ? <span className="text-mut">none linked</span> :
                      <div className="flex flex-wrap gap-x-2">{c.evidence.map((e: J, i: number) => <EvidenceRef key={i} caseId={caseData.id} id={e.id} ref_={e.evidence_ref} />)}</div>}</td>
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

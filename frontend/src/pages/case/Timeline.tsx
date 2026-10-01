import { useEffect, useMemo, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Loading, Section } from '../../components/ui'
import { EvidenceRef } from '../../components/EvidenceRef'
import type { J } from '../../types'

export default function Timeline() {
  const { caseData } = useCase()
  const [rows, setRows] = useState<J[] | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    api.get(`/cases/${caseData.id}/timeline`).then(setRows).catch((e) => setErr((e as Error).message))
  }, [caseData.id])

  const groups = useMemo(() => {
    const m = new Map<string, J[]>()
    ;(rows || []).forEach((r) => {
      const d = r.event_time.slice(0, 10)
      m.set(d, [...(m.get(d) || []), r])
    })
    return [...m.entries()]
  }, [rows])

  return (
    <div className="max-w-[1000px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title={`Timeline · ${rows?.length ?? 0} events`} right={<span className="lbl">TIMES IN IST · DATE-ONLY SHOWN AS --:--</span>}>
        {rows === null ? <Loading /> : rows.length === 0 ? <Empty>No timeline yet. Run analysis. The timeline lists evidence-backed events; it is not a complete log.</Empty> : (
          groups.map(([d, list]) => (
            <div key={d} className="mb-5">
              <div className="border-b border-line pb-1 mb-1" style={{ fontWeight: 700 }}>{fmt.date(d)}</div>
              <table className="tbl">
                <tbody>
                  {list.map((e) => (
                    <tr key={e.event_ref} className="row">
                      <td className="w-[80px] whitespace-nowrap">{fmt.clock(e.event_time)}</td>
                      <td className="w-[140px] whitespace-nowrap">{e.event_type}</td>
                      <td><b>{e.title}</b><div className="text-[12px] text-mut">{e.description}</div></td>
                      <td className="w-[120px] whitespace-nowrap">{e.evidence_ref ? <EvidenceRef caseId={caseData.id} id={e.evidence_id} ref_={e.evidence_ref} /> : <span className="lbl">STATEMENT</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))
        )}
      </Section>
    </div>
  )
}

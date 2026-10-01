import { useEffect, useState } from 'react'
import { api, fmt } from '../../lib/api'
import { useCase } from '../../components/CaseLayout'
import { Empty, ErrorBanner, Loading, Section, TrustTag } from '../../components/ui'
import type { J } from '../../types'

const SECTIONS: [string, string][] = [
  ['1_case_overview', 'Case overview'], ['2_party_statements', 'Party statements'], ['3_issues_identified', 'Issues identified'],
  ['4_evidence', 'Evidence'], ['5_evidence_claim_relationships', 'Evidence–claim relationships'],
  ['6_potential_contradictions', 'Potential contradictions'], ['7_legal_references', 'Relevant legal references'],
  ['8_hearing_history', 'Hearing history'], ['9_ai_assisted_analysis', 'AI-assisted analysis'],
  ['10_human_review', 'Human review'], ['11_human_decision', 'Human decision / preliminary resolution'],
  ['12_audit_information', 'Audit information'],
]

export default function Report() {
  const { caseData } = useCase()
  const [rep, setRep] = useState<J>(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => { api.get(`/cases/${caseData.id}/report.json`).then(setRep).catch((e) => setErr((e as Error).message)) }, [caseData.id])

  async function download(kind: 'json' | 'pdf') {
    setBusy(kind); setErr('')
    try {
      const blob = await api.download(`/cases/${caseData.id}/report.${kind}`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `VIVAD_${caseData.id}.${kind}`
      a.click()
      if (kind === 'pdf') window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    } catch (e) { setErr((e as Error).message) } finally { setBusy('') }
  }

  if (!rep) return <div><ErrorBanner message={err} onClose={() => setErr('')} /><Loading what="BUILDING REPORT" /></div>
  const decided = rep['11_human_decision']

  return (
    <div className="max-w-[900px]">
      <ErrorBanner message={err} onClose={() => setErr('')} />
      <Section title="VIVAD case report" right={<>
        <button className="btn" onClick={() => download('json')} disabled={!!busy}>[ EXPORT JSON ]</button>
        <button className="btn" onClick={() => download('pdf')} disabled={!!busy}>[ EXPORT PDF ]</button>
      </>}>
        {busy && <div className="blink mb-2">GENERATING {busy.toUpperCase()}…</div>}
        <div className="grid gap-3 sm:grid-cols-3 mb-3">
          <div className="border border-line p-3"><div className="lbl">Case</div><div>{rep.case.id}</div></div>
          <div className="border border-line p-3"><div className="lbl">Status</div><div>{fmt.label(rep.case.status)}</div></div>
          <div className="border border-line p-3"><div className="lbl">Decision</div><div>{decided ? fmt.label(decided.status) : 'NOT RECORDED'}</div></div>
        </div>
        {!decided && <Empty>No human decision has been recorded. The report can be generated, but the case is not resolved.</Empty>}
        <p className="text-mut">{rep.disclaimer}</p>
      </Section>

      <Section title="Report contents">
        <table className="tbl">
          <thead><tr><th>Section</th><th>Source</th></tr></thead>
          <tbody>
            {SECTIONS.map(([k, label]) => {
              const ai = k.startsWith('9_')
              const human = k.startsWith('10_') || k.startsWith('11_')
              return (
                <tr key={k}><td>{label}</td>
                  <td>{ai ? <TrustTag label="AI" /> : human ? <TrustTag label="HUMAN" /> : <TrustTag label="EVIDENCE" />}</td></tr>
              )
            })}
          </tbody>
        </table>
      </Section>

      <Section title="Evidence hashes">
        <table className="tbl"><thead><tr><th>Ref</th><th>File</th><th>SHA-256</th><th>Integrity</th></tr></thead>
          <tbody>{rep['4_evidence'].map((e: J) => (
            <tr key={e.evidence_ref}><td>{e.evidence_ref}</td><td>{e.filename}</td><td className="mono-hash">{e.sha256}</td><td>{e.verify_status || 'NOT CHECKED'}</td></tr>
          ))}</tbody>
        </table>
      </Section>
      <div className="lbl">AI-GENERATED SECTIONS AND HUMAN-VALIDATED SECTIONS ARE LABELLED SEPARATELY. A REPORT IS NOT A LEGALLY BINDING DECISION.</div>
    </div>
  )
}

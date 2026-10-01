import { Link } from 'react-router-dom'

// A clickable evidence reference, e.g. [E-002]. Opens the evidence detail panel.
export function EvidenceRef({ caseId, id, ref_ }: { caseId: string; id?: number | null; ref_: string }) {
  if (!id) return <span>[{ref_}]</span>
  return <Link className="link" to={`/cases/${caseId}/evidence/${id}`}>[{ref_}]</Link>
}

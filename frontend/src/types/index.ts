// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type J = any

export type Cls = 'DIRECT_IDENTIFIER_MATCH' | 'EXPLICIT_ASSOCIATION' | 'CONTEXTUAL_LEAD' | 'UNRESOLVED'

export const CLS_UI: Record<Cls, { sym: string; label: string; full: string; className: string }> = {
  DIRECT_IDENTIFIER_MATCH: { sym: '[✓]', label: 'VERIFIED', full: 'DIRECT IDENTIFIER MATCH', className: 'tag-verified' },
  EXPLICIT_ASSOCIATION: { sym: '[■]', label: 'DIRECT', full: 'EXPLICIT ASSOCIATION', className: 'tag-direct' },
  CONTEXTUAL_LEAD: { sym: '[□]', label: 'LEAD', full: 'CONTEXTUAL LEAD', className: 'tag-lead' },
  UNRESOLVED: { sym: '[?]', label: 'UNRESOLVED', full: 'UNRESOLVED', className: 'tag-unresolved' },
}

export type Role = 'CITIZEN' | 'RESPONDENT' | 'CASE_OFFICER' | 'REVIEWER' | 'CHAIR' | 'ADMIN'

export interface User {
  id: number
  username: string
  name: string
  role: Role
  email: string
}

export type TrustLabel = 'AI' | 'HUMAN' | 'EVIDENCE' | 'VERIFY'

export const TRUST_UI: Record<TrustLabel, { text: string; className: string }> = {
  AI: { text: 'AI-ASSISTED ANALYSIS', className: 'trust-ai' },
  HUMAN: { text: 'HUMAN-VALIDATED', className: 'trust-human' },
  EVIDENCE: { text: 'EVIDENCE-DERIVED', className: 'trust-evidence' },
  VERIFY: { text: 'REQUIRES VERIFICATION', className: 'trust-verify' },
}

export const STAFF_ROLES: Role[] = ['CASE_OFFICER', 'REVIEWER', 'CHAIR', 'ADMIN']

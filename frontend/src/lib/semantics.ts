// Central place that decides the semantic colour of a state. Colour answers "where should I
// look?", never decoration: green = verified/normal, amber = attention, red = critical, indigo = action/selected.
export type Variant = 'ok' | 'warn' | 'crit' | 'accent' | 'mut'

export function caseStatusVariant(status?: string): Variant {
  switch (status) {
    case 'RESOLVED':
    case 'CLOSED':
      return 'ok'
    case 'ESCALATED':
    case 'EVIDENCE_REQUESTED':
    case 'AWAITING_DECISION':
      return 'warn'
    case 'AWAITING_REVIEW':
    case 'AWAITING_COMMITTEE_REVIEW':
    case 'HEARING_SCHEDULED':
    case 'AWAITING_RESPONSE':
      return 'accent'
    default:
      return 'mut'
  }
}

export function claimVariant(status?: string): Variant {
  switch (status) {
    case 'SUPPORTED':
      return 'ok'
    case 'PARTIALLY_SUPPORTED':
    case 'REQUIRES_HUMAN_REVIEW':
      return 'warn'
    case 'CONTRADICTED':
    case 'UNSUPPORTED':
      return 'crit'
    default:
      return 'mut'
  }
}

export function contradictionVariant(status?: string): Variant {
  if (status === 'CONFIRMED_INCONSISTENCY') return 'crit'
  if (status === 'DISMISSED') return 'ok'
  if (status === 'ESCALATED') return 'warn'
  return 'warn'
}

export function classificationVariant(c: string): Variant {
  if (c === 'DIRECT_IDENTIFIER_MATCH') return 'ok'
  if (c === 'EXPLICIT_ASSOCIATION') return 'ok'
  if (c === 'CONTEXTUAL_LEAD') return 'warn'
  return 'crit'
}

export function trustVariant(label: string): Variant {
  if (label === 'HUMAN') return 'ok'
  if (label === 'EVIDENCE') return 'mut'
  if (label === 'AI') return 'warn'
  return 'warn' // REQUIRES VERIFICATION
}

export function severityVariant(score: number): Variant {
  if (score > 0) return 'crit'
  return 'ok'
}

// Consistent iconography for instant semantic recognition.
export const ICONS = {
  CASE: '◉', PARTIES: '●', STATEMENTS: '¶', EVIDENCE: '▣', TIMELINE: '⌁', GRAPH: '◎',
  CLAIMS: '⚑', CONTRADICTIONS: '⚠', LEGAL: '§', HEARINGS: '◷', REVIEW: '✓',
  DECISION: '⚖', AUDIT: '⛓', REPORT: '▤', OVERVIEW: '◈',
} as const

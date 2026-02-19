import type { ActivityStep } from '../../types/api'
import { formatDuration } from '../../utils/duration'

const KIND_PHRASES: Record<string, { singular: string; plural: string }> = {
  retrieve: { singular: 'searched 1 source', plural: 'searched {n} sources' },
  arxiv_search: { singular: 'searched arXiv', plural: 'searched arXiv {n} times' },
  ingest: { singular: 'added 1 paper', plural: 'added {n} papers' },
  list_papers: { singular: 'listed papers', plural: 'listed papers {n} times' },
  explore_citations: { singular: 'explored citations', plural: 'explored citations {n} times' },
  propose_ingest: { singular: 'proposed papers', plural: 'proposed papers {n} times' },
}

export interface CollapsedSummaryParts {
  text: string
  duration: string
}

export function buildCollapsedSummaryParts(
  activitySteps: ActivityStep[],
  totalDuration: number
): CollapsedSummaryParts {
  const counts = new Map<string, number>()
  for (const step of activitySteps) {
    if (step.kind === 'generating' || step.kind === 'refining') continue
    counts.set(step.kind, (counts.get(step.kind) ?? 0) + 1)
  }

  const parts: string[] = []
  for (const [kind, count] of counts) {
    const phrases = KIND_PHRASES[kind]
    if (!phrases) continue
    if (count === 1) {
      parts.push(phrases.singular)
    } else {
      parts.push(phrases.plural.replace('{n}', String(count)))
    }
  }

  const duration = formatDuration(totalDuration)

  if (parts.length === 0) {
    return { text: 'Completed', duration }
  }

  const sentence = parts[0].charAt(0).toUpperCase() + parts[0].slice(1) +
    (parts.length > 1 ? ', ' + parts.slice(1).join(', ') : '')

  return { text: sentence, duration }
}

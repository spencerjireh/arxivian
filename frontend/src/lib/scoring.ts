// Read-side helpers for score presentation (labels, band words, plain-language facts).

import type { DimensionDetail, ScoreBand, ScoreDimension } from '../types/api'

const BAND_WORDS: Record<ScoreBand, string> = { LOW: 'Weak', MED: 'Mixed', HIGH: 'Strong' }

/** The public word for a dimension's band; the data gate reads Pass / Fail. */
export function bandWord(dimension: DimensionDetail): string {
  if (dimension.dimension === 'data_availability') return dimension.level === 1 ? 'Pass' : 'Fail'
  return BAND_WORDS[dimension.band]
}

/**
 * Plain-language facts behind a dimension for the public row: every yes/no criterion that
 * held, and the chosen option of a choice question. Probabilities stay in Scoring details.
 */
export function dimensionFacts(dimension: DimensionDetail): string[] {
  const facts: string[] = []
  for (const j of dimension.judgments) {
    if (j.kind === 'noul' && j.answer === true) facts.push(judgmentLabel(j.key))
    if (j.kind === 'choice') facts.push(formatAnswer(j.answer))
  }
  return facts
}

const LOW_CONFIDENCE_THRESHOLD = 0.5

export function isLowConfidence(confidence: number): boolean {
  return confidence < LOW_CONFIDENCE_THRESHOLD
}

export const DIMENSION_ORDER: ScoreDimension[] = [
  'method_clarity',
  'resource_feasibility',
  'data_availability',
  'demand',
]

export const DIMENSION_LABELS: Record<ScoreDimension, string> = {
  method_clarity: 'Method clarity',
  resource_feasibility: 'Resource feasibility',
  data_availability: 'Data availability',
  demand: 'Demand',
}

/** Short labels under the card meter. */
export const DIMENSION_SHORT_LABELS: Record<ScoreDimension, string> = {
  method_clarity: 'Method',
  resource_feasibility: 'Compute',
  data_availability: 'Data',
  demand: 'Demand',
}

/** Human labels per level, in level order (0..max_level). */
export const LEVEL_LABELS: Record<ScoreDimension, string[]> = {
  method_clarity: ['0 criteria', '1 criterion', '2 criteria', '3 criteria', '4 criteria'],
  resource_feasibility: [
    'Cluster',
    'Multi-GPU node',
    'Datacenter GPU',
    'Consumer GPU',
    'Laptop / CPU',
  ],
  data_availability: ['Fail', 'Pass'],
  demand: ['Low', 'Medium', 'High'],
}

export const EVIDENCE_KIND_LABELS: Record<string, string> = {
  pseudocode: 'Pseudocode and algorithm spans',
  compute: 'Compute mentions',
  dataset: 'Dataset mentions',
  citation: 'Citation signal',
  code: 'Code mentions',
}

const JUDGMENT_LABELS: Record<string, string> = {
  algorithm_given: 'Algorithm or equations given',
  architecture_specified: 'Architecture specified',
  hyperparameters_stated: 'Hyperparameters stated',
  training_procedure_described: 'Training procedure described',
  compute_tier: 'Compute tier',
  compute_stated: 'Compute stated',
  pretrained_weights_released: 'Pretrained weights released',
  data_access: 'Data access',
  code_released: 'Code released',
  task_type: 'Task type',
  model_family: 'Model family',
}

export function judgmentLabel(key: string): string {
  return JUDGMENT_LABELS[key] ?? key.replace(/_/g, ' ')
}

export function formatAnswer(answer: string | number | boolean): string {
  if (typeof answer === 'boolean') return answer ? 'Yes' : 'No'
  return String(answer)
}

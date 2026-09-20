// Read-side helpers for score presentation (mirrors backend `schemas/scoring_state.py` bands).

import type { ScoreDimension, ScoreBand } from '../types/api'

export type { ScoreBand } from '../types/api'

/** LOW [0,40) - MED [40,70) - HIGH [70,100] */
export function bandFor(score: number): ScoreBand {
  if (score < 40) return 'LOW'
  if (score < 70) return 'MED'
  return 'HIGH'
}

const LOW_CONFIDENCE_THRESHOLD = 0.5

export function isLowConfidence(confidence: number): boolean {
  return confidence < LOW_CONFIDENCE_THRESHOLD
}

export const DIMENSION_LABELS: Record<ScoreDimension, string> = {
  method_clarity: 'Method clarity',
  resource_feasibility: 'Resource feasibility',
  data_availability: 'Data availability',
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

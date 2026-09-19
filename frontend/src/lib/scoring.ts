// Read-side helpers for score presentation (mirrors backend `schemas/scoring_state.py` bands).

import type { ScoreDimension } from '../types/api'

export type ScoreBand = 'LOW' | 'MED' | 'HIGH'

/** LOW [0,40) - MED [40,70) - HIGH [70,100] */
export function bandFor(score: number): ScoreBand {
  if (score < 40) return 'LOW'
  if (score < 70) return 'MED'
  return 'HIGH'
}

export const LOW_CONFIDENCE_THRESHOLD = 0.5

export function isLowConfidence(confidence: number): boolean {
  return confidence < LOW_CONFIDENCE_THRESHOLD
}

export const DIMENSION_LABELS: Record<ScoreDimension, string> = {
  method_clarity: 'Method clarity',
  resource_feasibility: 'Resource feasibility',
  data_availability: 'Data availability',
  demand: 'Demand',
}

import { makeFeedItem } from './feed'
import type { DimensionDetail, PaperScoreDetail } from '../../src/types/api'

export function makeDimension(overrides: Partial<DimensionDetail> = {}): DimensionDetail {
  return {
    dimension: 'method_clarity',
    band: 'HIGH',
    score: 80,
    level: 3,
    max_level: 4,
    expected: 3.2,
    probabilities: { '0': 0, '1': 0, '2': 0.2, '3': 0.5, '4': 0.3 },
    confidence: 0.5,
    judgments: [
      {
        key: 'algorithm_given',
        kind: 'noul',
        answer: true,
        probabilities: { yes: 0.9, no: 0.1 },
        confidence: 0.9,
        legend: null,
      },
    ],
    evidence: [
      { kind: 'pseudocode', text: 'Algorithm 1: for t in 1..T do', source: 'section 3' },
      { kind: 'compute', text: 'trained on 8 P100 GPUs', source: 'section 5' },
    ],
    reasoning: '3 of 4 criteria satisfied',
    ...overrides,
  }
}

export function makePaperScoreDetail(overrides: Partial<PaperScoreDetail> = {}): PaperScoreDetail {
  const item = makeFeedItem()
  return {
    paper: item.paper,
    rubric_version: 'v2',
    scored_at: '2026-08-04T00:00:00Z',
    scores: item.scores!,
    verdict: item.verdict!,
    signals: item.signals!,
    low_confidence: [],
    state: null,
    attributes: {
      code_released: {
        key: 'code_released',
        kind: 'noul',
        answer: true,
        probabilities: { yes: 0.8, no: 0.2 },
        confidence: 0.8,
        legend: null,
      },
      task_type: {
        key: 'task_type',
        kind: 'choice',
        answer: 'machine translation',
        probabilities: {},
        confidence: 0.7,
        legend: null,
      },
      model_family: {
        key: 'model_family',
        kind: 'choice',
        answer: 'transformer',
        probabilities: {},
        confidence: 0.9,
        legend: null,
      },
      code_evidence: [
        { kind: 'code', text: 'https://github.com/tensorflow/tensor2tensor', source: 'raw_text' },
      ],
    },
    dimensions: [
      makeDimension(),
      makeDimension({
        dimension: 'resource_feasibility',
        band: 'MED',
        score: 50,
        level: 2,
        confidence: 0.6,
      }),
      makeDimension({
        dimension: 'data_availability',
        band: 'HIGH',
        score: 100,
        level: 1,
        max_level: 1,
        probabilities: { '0': 0.05, '1': 0.95 },
        confidence: 0.95,
        evidence: [],
      }),
      makeDimension({
        dimension: 'demand',
        band: 'HIGH',
        score: 85,
        level: 2,
        max_level: 2,
        probabilities: { '0': 0, '1': 0, '2': 1 },
        confidence: 1,
        evidence: [],
      }),
    ],
    ...overrides,
  }
}

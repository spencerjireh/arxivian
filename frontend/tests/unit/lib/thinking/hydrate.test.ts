import { hydrateThinkingSteps } from '../../../../src/lib/thinking/hydrate'
import type { PersistedThinkingStep } from '../../../../src/types/api'

const SAMPLE_STEPS: PersistedThinkingStep[] = [
  {
    step: 'guardrail',
    message: 'Query is in scope',
    details: { score: 85, threshold: 50 },
    tool_name: null,
    started_at: '2026-02-15T10:00:00+00:00',
    completed_at: '2026-02-15T10:00:01+00:00',
  },
  {
    step: 'executing',
    message: 'retrieve completed',
    details: { tool_name: 'retrieve_chunks', success: true },
    tool_name: 'retrieve_chunks',
    started_at: '2026-02-15T10:00:02+00:00',
    completed_at: '2026-02-15T10:00:03+00:00',
  },
  {
    step: 'generation',
    message: 'Generation complete',
    details: null,
    tool_name: null,
    started_at: '2026-02-15T10:00:04+00:00',
    completed_at: '2026-02-15T10:00:05+00:00',
  },
]

describe('hydrateThinkingSteps', () => {
  it('returns undefined for null input', () => {
    expect(hydrateThinkingSteps(null)).toBeUndefined()
  })

  it('returns undefined for undefined input', () => {
    expect(hydrateThinkingSteps(undefined)).toBeUndefined()
  })

  it('returns undefined for empty array', () => {
    expect(hydrateThinkingSteps([])).toBeUndefined()
  })

  it('converts persisted steps with correct status and parsed dates', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    expect(result).toHaveLength(3)

    // All steps should have status 'complete'
    for (const step of result) {
      expect(step.status).toBe('complete')
    }

    // Verify date parsing
    const guardrail = result[0]
    expect(guardrail.startTime).toEqual(new Date('2026-02-15T10:00:00+00:00'))
    expect(guardrail.endTime).toEqual(new Date('2026-02-15T10:00:01+00:00'))
  })

  it('classifies internal steps correctly', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    // guardrail -> InternalStep
    expect(result[0].isInternal).toBe(true)
    if (result[0].isInternal) {
      expect(result[0].kind).toBe('guardrail')
    }

    // generation -> InternalStep
    expect(result[2].isInternal).toBe(true)
    if (result[2].isInternal) {
      expect(result[2].kind).toBe('generation')
    }
  })

  it('classifies executing steps with tool_name as ActivityStep', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    // executing with tool_name -> ActivityStep
    expect(result[1].isInternal).toBe(false)
    if (!result[1].isInternal) {
      expect(result[1].kind).toBe('retrieve')
      expect(result[1].toolName).toBe('retrieve_chunks')
    }
  })

  it('falls back to internal executing for unknown step types', () => {
    const unknown: PersistedThinkingStep[] = [
      {
        step: 'unknown_step',
        message: 'Something happened',
        details: null,
        tool_name: null,
        started_at: '2026-02-15T10:00:00+00:00',
        completed_at: '2026-02-15T10:00:01+00:00',
      },
    ]

    const result = hydrateThinkingSteps(unknown)!

    expect(result).toHaveLength(1)
    expect(result[0].isInternal).toBe(true)
    if (result[0].isInternal) {
      expect(result[0].kind).toBe('executing')
    }
  })

  it('assigns unique ids to each step', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!
    const ids = new Set(result.map((s) => s.id))
    expect(ids.size).toBe(result.length)
  })

  it('converts null details to undefined', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    expect(result[2].details).toBeUndefined() // generation had null details
    expect(result[0].details).toEqual({ score: 85, threshold: 50 }) // guardrail had details
  })
})

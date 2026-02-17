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
    details: { tool_name: 'retrieve', success: true },
    tool_name: 'retrieve',
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
    expect(guardrail.timestamp).toEqual(guardrail.startTime)
  })

  it('derives correct order from STEP_CONFIG', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    expect(result[0].order).toBe(0) // guardrail
    expect(result[1].order).toBe(3) // executing
    expect(result[2].order).toBe(5) // generation
  })

  it('preserves toolName for executing steps', () => {
    const result = hydrateThinkingSteps(SAMPLE_STEPS)!

    expect(result[1].toolName).toBe('retrieve')
    expect(result[0].toolName).toBeUndefined()
    expect(result[2].toolName).toBeUndefined()
  })

  it('falls back to executing for unknown step types', () => {
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
    expect(result[0].step).toBe('executing')
    expect(result[0].order).toBe(3) // executing order
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

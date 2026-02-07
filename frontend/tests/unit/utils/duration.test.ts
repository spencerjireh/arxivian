import type { ThinkingStep } from '../../../src/types/api'
import { getStepDuration, formatDuration, calculateTotalDuration } from '../../../src/utils/duration'

function makeStep(overrides: Partial<ThinkingStep> = {}): ThinkingStep {
  return {
    id: 'step-1',
    step: 'executing',
    message: 'test',
    status: 'running',
    timestamp: new Date(1000),
    startTime: new Date(1000),
    order: 3,
    ...overrides,
  }
}

describe('getStepDuration', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns elapsed time from startTime to endTime when complete', () => {
    const step = makeStep({
      startTime: new Date(1000),
      endTime: new Date(3500),
    })
    expect(getStepDuration(step)).toBe(2500)
  })

  it('returns elapsed time from startTime to now when still running', () => {
    vi.setSystemTime(new Date(5000))
    const step = makeStep({ startTime: new Date(2000), endTime: undefined })
    expect(getStepDuration(step)).toBe(3000)
  })
})

describe('formatDuration', () => {
  it('formats sub-second durations in ms', () => {
    expect(formatDuration(0)).toBe('0ms')
    expect(formatDuration(500)).toBe('500ms')
    expect(formatDuration(999)).toBe('999ms')
  })

  it('formats >= 1000ms in seconds with one decimal', () => {
    expect(formatDuration(1000)).toBe('1.0s')
    expect(formatDuration(1500)).toBe('1.5s')
    expect(formatDuration(12345)).toBe('12.3s')
  })
})

describe('calculateTotalDuration', () => {
  it('returns 0 for empty array', () => {
    expect(calculateTotalDuration([])).toBe(0)
  })

  it('returns duration for a single step', () => {
    const steps = [
      makeStep({ startTime: new Date(1000), endTime: new Date(3000) }),
    ]
    expect(calculateTotalDuration(steps)).toBe(2000)
  })

  it('spans from earliest start to latest end across multiple steps', () => {
    const steps = [
      makeStep({ startTime: new Date(1000), endTime: new Date(2000) }),
      makeStep({ startTime: new Date(1500), endTime: new Date(4000) }),
    ]
    expect(calculateTotalDuration(steps)).toBe(3000)
  })

  it('falls back to startTime when endTime is missing', () => {
    const steps = [
      makeStep({ startTime: new Date(1000), endTime: undefined }),
      makeStep({ startTime: new Date(3000), endTime: undefined }),
    ]
    expect(calculateTotalDuration(steps)).toBe(2000)
  })
})

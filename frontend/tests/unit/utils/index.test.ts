import { formatDate, truncateText, debounce } from '../../../src/utils/index'

describe('formatDate', () => {
  it('formats an ISO date string to locale date', () => {
    const result = formatDate('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })
})

describe('truncateText', () => {
  it('returns text unchanged when under limit', () => {
    expect(truncateText('hello', 10)).toBe('hello')
  })

  it('returns text unchanged when exactly at limit', () => {
    expect(truncateText('hello', 5)).toBe('hello')
  })

  it('truncates with ellipsis when over limit', () => {
    expect(truncateText('hello world', 5)).toBe('hello...')
  })
})

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('delays invocation by the specified time', () => {
    const fn = vi.fn()
    const debounced = debounce(fn, 200)

    debounced()
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(200)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('resets the timer on repeated calls', () => {
    const fn = vi.fn()
    const debounced = debounce(fn, 200)

    debounced()
    vi.advanceTimersByTime(100)
    debounced()
    vi.advanceTimersByTime(100)
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
  })
})

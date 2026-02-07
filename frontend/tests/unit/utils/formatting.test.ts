import { formatDetailKey, formatDetailValue } from '../../../src/utils/formatting'

describe('formatDetailKey', () => {
  it('converts snake_case to Title Case', () => {
    expect(formatDetailKey('retrieval_score')).toBe('Retrieval score')
  })

  it('splits camelCase with spaces', () => {
    expect(formatDetailKey('retrievalScore')).toBe('Retrieval Score')
  })

  it('capitalizes first letter', () => {
    expect(formatDetailKey('name')).toBe('Name')
  })
})

describe('formatDetailValue', () => {
  it('returns "-" for null or undefined', () => {
    expect(formatDetailValue('key', null)).toBe('-')
    expect(formatDetailValue('key', undefined)).toBe('-')
  })

  it('returns "Yes"/"No" for booleans', () => {
    expect(formatDetailValue('key', true)).toBe('Yes')
    expect(formatDetailValue('key', false)).toBe('No')
  })

  it('appends "%" for score/threshold keys', () => {
    expect(formatDetailValue('relevance_score', 85)).toBe('85%')
    expect(formatDetailValue('guardrail_threshold', 75)).toBe('75%')
  })

  it('returns plain number string for other numeric keys', () => {
    expect(formatDetailValue('count', 42)).toBe('42')
  })

  it('truncates long strings', () => {
    const long = 'a'.repeat(100)
    expect(formatDetailValue('key', long)).toBe('a'.repeat(80) + '...')
  })

  it('returns short strings unchanged', () => {
    expect(formatDetailValue('key', 'hello')).toBe('hello')
  })

  it('respects custom maxStringLength', () => {
    expect(formatDetailValue('key', 'abcdef', { maxStringLength: 3 })).toBe('abc...')
  })

  it('returns "-" for empty arrays', () => {
    expect(formatDetailValue('key', [])).toBe('-')
  })

  it('joins array elements with commas', () => {
    expect(formatDetailValue('key', ['a', 'b', 'c'])).toBe('a, b, c')
  })

  it('truncates arrays when maxArrayItems is set', () => {
    expect(formatDetailValue('key', ['a', 'b', 'c'], { maxArrayItems: 2 })).toBe('a, b...')
  })

  it('JSON-stringifies objects', () => {
    expect(formatDetailValue('key', { x: 1 })).toBe('{"x":1}')
  })
})

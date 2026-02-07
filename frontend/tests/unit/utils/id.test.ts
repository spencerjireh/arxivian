import { generateId, generateStepId, generateMessageId } from '../../../src/utils/id'

describe('generateId', () => {
  it('returns prefix-timestamp-random when prefix is given', () => {
    const id = generateId('test')
    const parts = id.split('-')
    expect(parts[0]).toBe('test')
    expect(Number(parts[1])).not.toBeNaN()
    expect(parts[2]).toMatch(/^[a-z0-9]+$/)
  })

  it('returns timestamp-random when no prefix is given', () => {
    const id = generateId()
    const parts = id.split('-')
    expect(parts).toHaveLength(2)
    expect(Number(parts[0])).not.toBeNaN()
    expect(parts[1]).toMatch(/^[a-z0-9]+$/)
  })

  it('produces unique ids on successive calls', () => {
    const ids = new Set(Array.from({ length: 50 }, () => generateId()))
    expect(ids.size).toBe(50)
  })
})

describe('generateStepId', () => {
  it('starts with "step-"', () => {
    expect(generateStepId()).toMatch(/^step-/)
  })
})

describe('generateMessageId', () => {
  it('has no prefix (timestamp-random)', () => {
    const id = generateMessageId()
    const parts = id.split('-')
    expect(parts).toHaveLength(2)
    expect(Number(parts[0])).not.toBeNaN()
  })
})

import { formatAuthors, formatDate } from '@/lib/formatting'

describe('formatAuthors', () => {
  it('lists up to three authors', () => {
    expect(formatAuthors(['A', 'B', 'C'])).toBe('A, B, C')
  })

  it('collapses the rest into a count', () => {
    expect(formatAuthors(['A', 'B', 'C', 'D', 'E'])).toBe('A, B, C +2 more')
  })
})

describe('formatDate', () => {
  it('renders a short date', () => {
    expect(formatDate('2024-01-01T00:00:00Z')).toMatch(/Jan 1, 2024|Dec 31, 2023/)
  })
})

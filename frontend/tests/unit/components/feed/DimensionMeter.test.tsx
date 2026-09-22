import { render, screen, within } from '@testing-library/react'
import DimensionMeter from '../../../../src/components/feed/DimensionMeter'

const scores = {
  method_clarity: 80,
  resource_feasibility: 49.6,
  data_availability: 100,
  demand: 20,
}

describe('DimensionMeter', () => {
  it('renders one meter per dimension in rubric order with the rounded value as its fill', () => {
    render(<DimensionMeter scores={scores} />)
    const list = screen.getByRole('list', { name: 'Implementability meter' })
    const meters = within(list).getAllByRole('meter')
    expect(meters.map((m) => m.getAttribute('aria-label'))).toEqual([
      'Method 80 of 100',
      'Compute 50 of 100',
      'Data 100 of 100',
      'Demand 20 of 100',
    ])
    expect((meters[1].firstElementChild as HTMLElement).style.width).toBe('50%')
    expect(meters[1]).toHaveAttribute('aria-valuemin', '0')
    expect(meters[1]).toHaveAttribute('aria-valuemax', '100')
  })

  it('uses the full labels at the md size', () => {
    render(<DimensionMeter scores={scores} size="md" />)
    expect(screen.getByText('Resource feasibility')).toBeInTheDocument()
    expect(screen.queryByText('Compute')).not.toBeInTheDocument()
  })

  it('renders a hollow segment for a null value instead of a low fill', () => {
    render(<DimensionMeter scores={{ ...scores, demand: null }} />)
    expect(screen.getAllByRole('meter')).toHaveLength(3)
    const hollow = screen.getByRole('img', { name: 'Demand not available' })
    expect(hollow).toHaveAttribute('title', 'Demand: not available')
    expect(hollow.querySelector('div')).toBeNull()
  })
})

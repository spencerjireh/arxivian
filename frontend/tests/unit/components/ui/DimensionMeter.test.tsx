import { render, screen, within } from '@testing-library/react'
import DimensionMeter from '@/components/ui/DimensionMeter'

const scores = {
  method_clarity: 80,
  resource_feasibility: 49.6,
  data_availability: 100,
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

  it('draws only the requested dimensions, in that order', () => {
    render(
      <DimensionMeter scores={scores} dimensions={['method_clarity', 'resource_feasibility']} />
    )
    const list = screen.getByRole('list', { name: 'Implementability meter' })
    expect(list).toHaveClass('grid-cols-2')
    expect(
      within(list)
        .getAllByRole('meter')
        .map((m) => m.getAttribute('data-dimension'))
    ).toEqual(['method_clarity', 'resource_feasibility'])
    expect(screen.queryByText('Data')).not.toBeInTheDocument()
  })

  it('hatches a low-confidence dimension and says so, without hiding it', () => {
    render(<DimensionMeter scores={scores} lowConfidence={['resource_feasibility']} />)
    const low = screen.getByRole('meter', { name: 'Compute 50 of 100 (low confidence)' })
    expect(low).toHaveAttribute('title', 'Compute: 50 (low confidence)')
    expect(low).toHaveAttribute('data-confidence', 'low')
    expect(low.firstElementChild).toHaveClass('meter-hatched')
    expect(low.firstElementChild).not.toHaveClass('bg-stone-800')
    const solid = screen.getByRole('meter', { name: 'Method 80 of 100' })
    expect(solid).not.toHaveAttribute('data-confidence')
    expect(solid.firstElementChild).toHaveClass('bg-stone-800')
  })

  it('keeps the hollow segment for a null value even when flagged low confidence', () => {
    render(
      <DimensionMeter
        scores={{ ...scores, resource_feasibility: null }}
        lowConfidence={['resource_feasibility']}
      />
    )
    expect(screen.getByRole('img', { name: 'Compute not available' })).toBeInTheDocument()
  })

  it('renders a hollow segment for a null value instead of a low fill', () => {
    render(<DimensionMeter scores={{ ...scores, resource_feasibility: null }} />)
    expect(screen.getAllByRole('meter')).toHaveLength(2)
    const hollow = screen.getByRole('img', { name: 'Compute not available' })
    expect(hollow).toHaveAttribute('title', 'Compute: not available')
    expect(hollow.querySelector('div')).toBeNull()
  })
})

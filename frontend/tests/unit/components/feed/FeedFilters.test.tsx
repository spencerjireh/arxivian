import { render, screen, fireEvent } from '@testing-library/react'
import WeekSelector from '../../../../src/components/feed/WeekSelector'
import FeedFilterBar from '../../../../src/components/feed/FeedFilterBar'

const weeks = [
  { week_start: '2026-07-27', paper_count: 5 },
  { week_start: '2026-08-10', paper_count: 1 },
  { week_start: '2026-08-03', paper_count: 12 },
]

describe('WeekSelector', () => {
  it('lists weeks newest first with counts and reports a change', () => {
    const onChange = vi.fn()
    render(<WeekSelector weeks={weeks} value="2026-08-03" onChange={onChange} />)
    const options = screen.getAllByRole('option').map((o) => o.textContent)
    expect(options).toEqual([
      'Week of Aug 10 (1 paper)',
      'Week of Aug 3 (12 papers)',
      'Week of Jul 27 (5 papers)',
    ])
    fireEvent.change(screen.getByLabelText('Digest week'), { target: { value: '2026-07-27' } })
    expect(onChange).toHaveBeenCalledWith('2026-07-27')
  })

  it('steps older / newer and disables at the ends', () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <WeekSelector weeks={weeks} value="2026-08-03" onChange={onChange} />
    )
    fireEvent.click(screen.getByRole('button', { name: 'Older week' }))
    expect(onChange).toHaveBeenLastCalledWith('2026-07-27')
    fireEvent.click(screen.getByRole('button', { name: 'Newer week' }))
    expect(onChange).toHaveBeenLastCalledWith('2026-08-10')

    rerender(<WeekSelector weeks={weeks} value="2026-08-10" onChange={onChange} />)
    expect(screen.getByRole('button', { name: 'Newer week' })).toBeDisabled()
    rerender(<WeekSelector weeks={weeks} value="2026-07-27" onChange={onChange} />)
    expect(screen.getByRole('button', { name: 'Older week' })).toBeDisabled()
  })
})

describe('FeedFilterBar', () => {
  function mountBar(props: Partial<React.ComponentProps<typeof FeedFilterBar>> = {}) {
    const onChange = vi.fn()
    render(
      <FeedFilterBar
        categories={['cs.CV', 'cs.LG']}
        category={undefined}
        minScore={undefined}
        includeDismissed={false}
        showDismissed
        onChange={onChange}
        {...props}
      />
    )
    return onChange
  }

  it('changes category, min score and dismissed independently', () => {
    const onChange = mountBar()
    fireEvent.change(screen.getByLabelText('Category'), { target: { value: 'cs.LG' } })
    expect(onChange).toHaveBeenLastCalledWith({ category: 'cs.LG' })
    fireEvent.click(screen.getByRole('button', { name: '70+' }))
    expect(onChange).toHaveBeenLastCalledWith({ minScore: 70 })
    fireEvent.click(screen.getByRole('button', { name: 'Any' }))
    expect(onChange).toHaveBeenLastCalledWith({ minScore: undefined })
    fireEvent.click(screen.getByLabelText('Show dismissed'))
    expect(onChange).toHaveBeenLastCalledWith({ includeDismissed: true })
  })

  it('hides the dismissed toggle for an anonymous reader and ignores it in Clear filters', () => {
    mountBar({ showDismissed: false, includeDismissed: true })
    expect(screen.queryByLabelText('Show dismissed')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
  })

  it('shows Clear filters only when something is set and clears everything', () => {
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
    const onChange = mountBar({ category: 'cs.LG', minScore: 40 })
    expect(screen.getByRole('button', { name: '40+' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(onChange).toHaveBeenLastCalledWith({
      category: undefined,
      minScore: undefined,
      includeDismissed: false,
    })
  })
})

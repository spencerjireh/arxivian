import { render, screen, fireEvent } from '@testing-library/react'
import FeedFilters from '@/features/feed/components/FeedFilters'
import WeekSelector from '@/features/feed/components/WeekSelector'
import { EMPTY_VIEW } from '@/features/feed/lib/feedView'

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

describe('FeedFilters', () => {
  function mount(props: Partial<React.ComponentProps<typeof FeedFilters>> = {}) {
    const onChange = vi.fn()
    const onDismissedChange = vi.fn()
    const onClear = vi.fn()
    render(
      <FeedFilters
        view={EMPTY_VIEW}
        categories={['cs.CV', 'cs.LG']}
        showDismissed
        includeDismissed={false}
        onChange={onChange}
        onDismissedChange={onDismissedChange}
        onClear={onClear}
        filterCount={0}
        {...props}
      />
    )
    return { onChange, onDismissedChange, onClear }
  }

  it('adds and removes a category', () => {
    const { onChange } = mount({ view: { ...EMPTY_VIEW, categories: ['cs.CV'] } })
    fireEvent.click(screen.getByLabelText('cs.LG'))
    expect(onChange).toHaveBeenLastCalledWith({ categories: ['cs.CV', 'cs.LG'] })
    fireEvent.click(screen.getByLabelText('cs.CV'))
    expect(onChange).toHaveBeenLastCalledWith({ categories: [] })
  })

  it('picks a compute tier and goes back to any', () => {
    const { onChange } = mount({ view: { ...EMPTY_VIEW, tier: 'laptop' } })
    expect(screen.getByLabelText('Laptop / CPU')).toBeChecked()
    fireEvent.click(screen.getByLabelText('Consumer GPU'))
    expect(onChange).toHaveBeenLastCalledWith({ tier: 'consumer' })
    fireEvent.click(screen.getByLabelText('Any hardware'))
    expect(onChange).toHaveBeenLastCalledWith({ tier: null })
  })

  it('toggles code released and show dismissed independently', () => {
    const { onChange, onDismissedChange } = mount()
    fireEvent.click(screen.getByLabelText('Code released'))
    expect(onChange).toHaveBeenLastCalledWith({ code: true })
    fireEvent.click(screen.getByLabelText('Show dismissed'))
    expect(onDismissedChange).toHaveBeenLastCalledWith(true)
    expect(onChange).toHaveBeenCalledTimes(1)
  })

  it('hides the dismissed toggle for an anonymous reader', () => {
    mount({ showDismissed: false })
    expect(screen.queryByLabelText('Show dismissed')).not.toBeInTheDocument()
  })

  it('shows Clear filters only when something is set', () => {
    mount()
    expect(screen.queryByRole('button', { name: 'Clear filters' })).not.toBeInTheDocument()
    const { onClear } = mount({ filterCount: 2 })
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(onClear).toHaveBeenCalledTimes(1)
  })
})

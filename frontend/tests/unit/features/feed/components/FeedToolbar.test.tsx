import { render, screen, fireEvent, within } from '@testing-library/react'
import FeedToolbar from '@/features/feed/components/FeedToolbar'
import { EMPTY_VIEW } from '@/features/feed/lib/feedView'

function mount(props: Partial<React.ComponentProps<typeof FeedToolbar>> = {}) {
  const handlers = {
    onViewChange: vi.fn(),
    onQueryChange: vi.fn(),
    onWeekChange: vi.fn(),
    onDismissedChange: vi.fn(),
    onClear: vi.fn(),
  }
  render(
    <FeedToolbar
      view={EMPTY_VIEW}
      query=""
      weeks={[
        { week_start: '2026-08-03', paper_count: 3 },
        { week_start: '2026-07-27', paper_count: 5 },
      ]}
      week="2026-08-03"
      categories={['cs.LG']}
      showDismissed
      includeDismissed={false}
      filterCount={0}
      {...handlers}
      {...props}
    />
  )
  return handlers
}

describe('FeedToolbar', () => {
  it('switches the sort and marks the active one', () => {
    const { onViewChange } = mount({ view: { ...EMPTY_VIEW, sort: 'newest' } })
    const group = screen.getByRole('group', { name: 'Sort' })
    expect(within(group).getByRole('button', { name: 'Newest' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    fireEvent.click(within(group).getByRole('button', { name: 'Ranked' }))
    expect(onViewChange).toHaveBeenCalledWith({ sort: 'ranked' })
  })

  it('reports search input and week changes', () => {
    const { onQueryChange, onWeekChange } = mount()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search this week' }), {
      target: { value: 'attention' },
    })
    expect(onQueryChange).toHaveBeenCalledWith('attention')
    fireEvent.change(screen.getByLabelText('Digest week'), { target: { value: '2026-07-27' } })
    expect(onWeekChange).toHaveBeenCalledWith('2026-07-27')
  })

  it('opens the Filters dialog from a badge-counted trigger and wires its controls', () => {
    const { onViewChange, onClear } = mount({ filterCount: 2 })
    const trigger = screen.getByRole('button', { name: 'Filters 2' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Filters' })
    fireEvent.click(within(dialog).getByLabelText('cs.LG'))
    expect(onViewChange).toHaveBeenCalledWith({ categories: ['cs.LG'] })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Clear filters' }))
    expect(onClear).toHaveBeenCalledTimes(1)
  })

  it('shows no badge without filters', () => {
    mount()
    expect(screen.getByRole('button', { name: 'Filters' })).toBeInTheDocument()
  })
})

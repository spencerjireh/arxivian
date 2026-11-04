// Feed: the sticky bar under the top nav (sort tabs, search, week selector, Filters popover).
import clsx from 'clsx'
import { SlidersHorizontal } from 'lucide-react'
import Chip from '@/components/ui/Chip'
import Popover from '@/components/ui/Popover'
import { selectClass } from '@/lib/formClasses'
import FeedFilters from './FeedFilters'
import WeekSelector from './WeekSelector'
import type { FeedSort, FeedView } from '../lib/feedView'
import type { AvailableWeek } from '@/types/api'

interface FeedToolbarProps {
  view: FeedView
  onViewChange: (patch: Partial<FeedView>) => void
  /** The search draft: filters as you type, while the URL write is debounced by the page. */
  query: string
  onQueryChange: (query: string) => void
  weeks: AvailableWeek[]
  week: string
  onWeekChange: (week: string) => void
  categories: string[]
  showDismissed: boolean
  includeDismissed: boolean
  onDismissedChange: (next: boolean) => void
  onClear: () => void
  filterCount: number
}

const SORTS: { value: FeedSort; label: string }[] = [
  { value: 'ranked', label: 'Ranked' },
  { value: 'newest', label: 'Newest' },
]

/**
 * Sticks right under the 4rem top nav. One row from `sm` up (tabs, search, week, Filters);
 * on phones the flex order puts Filters beside the tabs, then the week selector, then a
 * full-width search, and the Filters panel spans the bar (the inner row is its anchor).
 */
export default function FeedToolbar({
  view,
  onViewChange,
  query,
  onQueryChange,
  weeks,
  week,
  onWeekChange,
  categories,
  showDismissed,
  includeDismissed,
  onDismissedChange,
  onClear,
  filterCount,
}: FeedToolbarProps) {
  return (
    <div className="sticky top-16 z-40 -mx-6 border-b border-stone-200 bg-[#fafaf9]/95 px-6 py-2 backdrop-blur-sm">
      <div className="relative flex flex-wrap items-center gap-2">
        <div role="group" aria-label="Sort" className="order-1 flex gap-1">
          {SORTS.map(({ value, label }) => {
            const active = view.sort === value
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => onViewChange({ sort: value })}
                className={clsx(
                  'border-b-2 px-2 py-1.5 text-sm transition-colors duration-150',
                  active
                    ? 'border-stone-900 font-medium text-stone-900'
                    : 'border-transparent text-stone-500 hover:text-stone-800'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>

        <input
          type="search"
          aria-label="Search this week"
          placeholder="Search this week"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          className={clsx(selectClass, 'order-4 w-full sm:order-2 sm:ml-auto sm:w-44')}
        />

        <div className="order-3 w-full sm:w-auto">
          <WeekSelector weeks={weeks} value={week} onChange={onWeekChange} />
        </div>

        <div className="order-2 ml-auto sm:order-4 sm:ml-0">
          <Popover
            label="Filters"
            triggerProps={{
              variant: 'secondary',
              size: 'sm',
              leftIcon: <SlidersHorizontal className="h-4 w-4" strokeWidth={1.5} />,
            }}
            trigger={<>Filters {filterCount > 0 && <Chip size="sm">{filterCount}</Chip>}</>}
          >
            <FeedFilters
              view={view}
              categories={categories}
              showDismissed={showDismissed}
              includeDismissed={includeDismissed}
              onChange={onViewChange}
              onDismissedChange={onDismissedChange}
              onClear={onClear}
              filterCount={filterCount}
            />
          </Popover>
        </div>
      </div>
    </div>
  )
}

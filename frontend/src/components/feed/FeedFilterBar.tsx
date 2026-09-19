import clsx from 'clsx'
import Button from '../ui/Button'
import { segmentedActiveClass, segmentedInactiveClass, selectClass } from '../../lib/formClasses'

export interface FeedFilters {
  category?: string
  minScore?: number
  includeDismissed?: boolean
}

interface FeedFilterBarProps {
  categories: string[]
  category: string | undefined
  minScore: number | undefined
  includeDismissed: boolean
  onChange: (next: FeedFilters) => void
}

const MIN_SCORE_OPTIONS: { value: number | undefined; label: string }[] = [
  { value: undefined, label: 'Any' },
  { value: 40, label: '40+' },
  { value: 70, label: '70+' },
]

/** Category, minimum composite (band thresholds), and the dismissed toggle. */
export default function FeedFilterBar({ categories, category, minScore, includeDismissed, onChange }: FeedFilterBarProps) {
  const hasFilters = Boolean(category) || minScore !== undefined || includeDismissed
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        aria-label="Category"
        value={category ?? ''}
        onChange={(e) => onChange({ category: e.target.value || undefined })}
        className={clsx(selectClass, 'w-44')}
      >
        <option value="">All categories</option>
        {categories.map((c) => (
          <option key={c} value={c}>
            {c}
          </option>
        ))}
      </select>

      <div className="inline-flex rounded-lg overflow-hidden border border-stone-200" role="group" aria-label="Minimum score">
        {MIN_SCORE_OPTIONS.map(({ value, label }) => (
          <button
            key={label}
            type="button"
            onClick={() => onChange({ minScore: value })}
            aria-pressed={minScore === value}
            className={clsx(
              'px-3 py-2 text-sm transition-colors duration-150',
              minScore === value ? segmentedActiveClass : segmentedInactiveClass,
            )}
          >
            {label}
          </button>
        ))}
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-stone-600">
        <input
          type="checkbox"
          className="accent-stone-700"
          checked={includeDismissed}
          onChange={(e) => onChange({ includeDismissed: e.target.checked })}
        />
        Show dismissed
      </label>

      {hasFilters && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange({ category: undefined, minScore: undefined, includeDismissed: false })}
        >
          Clear filters
        </Button>
      )}
    </div>
  )
}

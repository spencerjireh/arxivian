// Feed: the Filters popover body (categories, compute tier, code released, show dismissed, clear).
import Button from '@/components/ui/Button'
import { LEVEL_LABELS } from '@/lib/scoring'
import {
  TIER_MIN_LEVEL,
  TIER_OPTIONS,
  type ComputeTierFilter,
  type FeedView,
} from '../lib/feedView'

interface FeedFiltersProps {
  view: FeedView
  categories: string[]
  /** Dismissals are per-user state, so the toggle exists only for a signed-in reader. */
  showDismissed: boolean
  includeDismissed: boolean
  onChange: (patch: Partial<FeedView>) => void
  onDismissedChange: (next: boolean) => void
  onClear: () => void
  filterCount: number
}

const checkboxClass = 'accent-stone-700'
const rowClass = 'flex items-center gap-2 text-sm text-stone-700'
const legendClass = 'mb-1.5 text-xs font-medium text-stone-500'

/** Native controls only; every change goes straight to the URL through the page. */
export default function FeedFilters({
  view,
  categories,
  showDismissed,
  includeDismissed,
  onChange,
  onDismissedChange,
  onClear,
  filterCount,
}: FeedFiltersProps) {
  const toggleCategory = (category: string, checked: boolean) =>
    onChange({
      categories: checked
        ? [...view.categories, category]
        : view.categories.filter((c) => c !== category),
    })

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className={legendClass}>Categories</legend>
        <div className="max-h-48 space-y-1 overflow-y-auto">
          {categories.map((category) => (
            <label key={category} className={rowClass}>
              <input
                type="checkbox"
                className={checkboxClass}
                checked={view.categories.includes(category)}
                onChange={(e) => toggleCategory(category, e.target.checked)}
              />
              <span className="font-mono text-xs">{category}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset>
        <legend className={legendClass}>Runs on at most</legend>
        <div className="space-y-1">
          <label className={rowClass}>
            <input
              type="radio"
              name="tier"
              className={checkboxClass}
              checked={view.tier === null}
              onChange={() => onChange({ tier: null })}
            />
            Any hardware
          </label>
          {TIER_OPTIONS.map((tier: ComputeTierFilter) => (
            <label key={tier} className={rowClass}>
              <input
                type="radio"
                name="tier"
                className={checkboxClass}
                checked={view.tier === tier}
                onChange={() => onChange({ tier })}
              />
              {LEVEL_LABELS.resource_feasibility[TIER_MIN_LEVEL[tier]]}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="space-y-1">
        <label className={rowClass}>
          <input
            type="checkbox"
            className={checkboxClass}
            checked={view.code}
            onChange={(e) => onChange({ code: e.target.checked })}
          />
          Code released
        </label>
        {showDismissed && (
          <label className={rowClass}>
            <input
              type="checkbox"
              className={checkboxClass}
              checked={includeDismissed}
              onChange={(e) => onDismissedChange(e.target.checked)}
            />
            Show dismissed
          </label>
        )}
      </div>

      {filterCount > 0 && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear filters
        </Button>
      )}
    </div>
  )
}

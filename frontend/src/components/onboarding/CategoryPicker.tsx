import clsx from 'clsx'
import { ARXIV_CATEGORIES } from '../../lib/arxivCategories'

interface CategoryPickerProps {
  value: string[]
  onChange: (value: string[]) => void
  error?: string
}

/** Toggle-chip grid over the curated arXiv categories. */
export default function CategoryPicker({ value, onChange, error }: CategoryPickerProps) {
  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id])

  return (
    <div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2" role="group" aria-label="arXiv categories">
        {ARXIV_CATEGORIES.map((cat) => {
          const selected = value.includes(cat.id)
          return (
            <button
              key={cat.id}
              type="button"
              aria-pressed={selected}
              onClick={() => toggle(cat.id)}
              className={clsx(
                'text-left rounded-lg border px-3 py-2 transition-colors duration-150',
                selected
                  ? 'bg-stone-900 border-stone-900 text-white'
                  : 'bg-white border-stone-200 text-stone-700 hover:border-stone-300',
              )}
            >
              <span className="block font-mono text-xs">{cat.id}</span>
              <span className={clsx('block text-xs', selected ? 'text-stone-300' : 'text-stone-500')}>
                {cat.label}
              </span>
            </button>
          )
        })}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  )
}

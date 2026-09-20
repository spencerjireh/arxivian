import { Cloud, Cpu, Laptop } from 'lucide-react'
import clsx from 'clsx'
import type { ComputeProfile } from '../../types/api'

interface ComputeProfilePickerProps {
  value?: ComputeProfile | null
  onChange: (value: ComputeProfile) => void
  error?: string
}

const OPTIONS: { value: ComputeProfile; label: string; detail: string; icon: typeof Laptop }[] = [
  { value: 'laptop', label: 'Laptop', detail: 'CPU or a small notebook GPU', icon: Laptop },
  { value: 'single_gpu', label: 'Single GPU', detail: 'One consumer or datacenter GPU', icon: Cpu },
  { value: 'cloud', label: 'Cloud budget', detail: 'Multi-GPU nodes for a few days', icon: Cloud },
]

/** Declared compute reality; the feed ranks papers that fit it first. */
export default function ComputeProfilePicker({
  value,
  onChange,
  error,
}: ComputeProfilePickerProps) {
  return (
    <div>
      <div
        className="grid grid-cols-1 gap-2 sm:grid-cols-3"
        role="radiogroup"
        aria-label="Compute profile"
      >
        {OPTIONS.map(({ value: v, label, detail, icon: Icon }) => {
          const selected = value === v
          return (
            <button
              key={v}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onChange(v)}
              className={clsx(
                'flex items-start gap-3 rounded-lg border px-4 py-3 text-left transition-colors duration-150',
                selected
                  ? 'border-stone-900 bg-stone-900 text-white'
                  : 'border-stone-200 bg-white text-stone-700 hover:border-stone-300'
              )}
            >
              <Icon className="mt-0.5 h-5 w-5 shrink-0" strokeWidth={1.5} />
              <span>
                <span className="block text-sm font-medium">{label}</span>
                <span
                  className={clsx('block text-xs', selected ? 'text-stone-300' : 'text-stone-500')}
                >
                  {detail}
                </span>
              </span>
            </button>
          )
        })}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  )
}

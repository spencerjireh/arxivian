// UI primitive: a centered icon-in-a-circle block for empty and error states.
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface StatusBlockProps {
  icon: LucideIcon
  tone?: 'neutral' | 'error'
  title: string
  /** A second, quieter line; pass children instead when it needs markup. */
  hint?: string
  children?: React.ReactNode
}

export default function StatusBlock({
  icon: Icon,
  tone = 'neutral',
  title,
  hint,
  children,
}: StatusBlockProps) {
  const error = tone === 'error'
  return (
    <div className="flex flex-col items-center justify-center py-24">
      <div
        className={clsx(
          'mb-3 flex h-12 w-12 items-center justify-center rounded-full',
          error ? 'bg-[var(--color-error-soft)]' : 'bg-stone-100'
        )}
      >
        <Icon
          className={clsx('h-5 w-5', error ? 'text-[var(--color-error)]' : 'text-stone-400')}
          strokeWidth={1.5}
        />
      </div>
      <p className={clsx('text-sm', error ? 'text-stone-500' : 'font-medium text-stone-700')}>
        {title}
      </p>
      {hint && <p className="mt-1 text-sm text-stone-400">{hint}</p>}
      {children}
    </div>
  )
}

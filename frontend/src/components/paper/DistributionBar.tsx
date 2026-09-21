// Paper detail: level probability distribution as a segmented bar.
import clsx from 'clsx'

interface DistributionBarProps {
  probabilities: Record<string, number>
  level: number
  maxLevel: number
  labels?: string[]
  className?: string
}

/** One segment per level, width = probability mass; the argmax level is highlighted. */
export default function DistributionBar({
  probabilities,
  level,
  maxLevel,
  labels,
  className,
}: DistributionBarProps) {
  const levels = Array.from({ length: maxLevel + 1 }, (_, i) => i)
  const description = levels
    .map(
      (i) => `${labels?.[i] ?? `Level ${i}`}: ${Math.round((probabilities[String(i)] ?? 0) * 100)}%`
    )
    .join(', ')

  return (
    <div
      role="img"
      aria-label={description}
      className={clsx('flex h-2 w-full gap-0.5 overflow-hidden rounded-full', className)}
    >
      {levels.map((i) => {
        const p = probabilities[String(i)] ?? 0
        return (
          <div
            key={i}
            data-level={i}
            data-argmax={i === level ? 'true' : undefined}
            title={`${labels?.[i] ?? `Level ${i}`}: ${Math.round(p * 100)}%`}
            className={clsx('h-full rounded-sm', i === level ? 'bg-amber-700' : 'bg-stone-200')}
            style={{ width: `${Math.max(p * 100, p > 0 ? 2 : 0)}%` }}
          />
        )
      })}
    </div>
  )
}

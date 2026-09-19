import { AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { bandFor, type ScoreBand } from '../../lib/scoring'

interface ScoreBadgeProps {
  score: number
  size?: 'sm' | 'lg'
  lowConfidence?: boolean
  lowConfidenceTitle?: string
  className?: string
}

const bandClasses: Record<ScoreBand, string> = {
  LOW: 'bg-stone-100 text-stone-600',
  MED: 'bg-[var(--color-accent-soft)] text-amber-800',
  HIGH: 'bg-[var(--color-success-soft)] text-[var(--color-success)]',
}

/** Composite implementability score. Visually secondary to the verdict line. */
export default function ScoreBadge({
  score,
  size = 'sm',
  lowConfidence = false,
  lowConfidenceTitle = 'Low confidence',
  className,
}: ScoreBadgeProps) {
  const band = bandFor(score)
  const rounded = Math.round(score)
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-lg font-mono tabular-nums',
        size === 'lg' ? 'px-3 py-1.5 text-xl' : 'px-2 py-0.5 text-sm',
        bandClasses[band],
        className,
      )}
      aria-label={`Score ${rounded} of 100, ${band.toLowerCase()}`}
      data-band={band}
    >
      <span className="font-semibold">{rounded}</span>
      <span className={clsx('uppercase tracking-wide', size === 'lg' ? 'text-xs' : 'text-[10px]')}>
        {band}
      </span>
      {lowConfidence && (
        <AlertCircle
          className={size === 'lg' ? 'w-4 h-4' : 'w-3 h-3'}
          strokeWidth={1.5}
          aria-label={lowConfidenceTitle}
        >
          <title>{lowConfidenceTitle}</title>
        </AlertCircle>
      )}
    </span>
  )
}

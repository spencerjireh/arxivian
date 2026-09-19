import clsx from 'clsx'

type ChipTone = 'neutral' | 'accent' | 'success' | 'info' | 'warning'
type ChipSize = 'sm' | 'md'

interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: ChipTone
  size?: ChipSize
  icon?: React.ReactNode
}

const toneClasses: Record<ChipTone, string> = {
  neutral: 'bg-stone-100 text-stone-600',
  accent: 'bg-[var(--color-accent-soft)] text-amber-800',
  success: 'bg-[var(--color-success-soft)] text-[var(--color-success)]',
  info: 'bg-[var(--color-info-soft)] text-[var(--color-info)]',
  warning: 'bg-amber-50 text-amber-700',
}

const sizeClasses: Record<ChipSize, string> = {
  sm: 'text-[11px] px-2 py-0.5',
  md: 'text-xs px-2.5 py-1',
}

export default function Chip({
  tone = 'neutral',
  size = 'sm',
  icon,
  className,
  children,
  ...props
}: ChipProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap',
        toneClasses[tone],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  )
}

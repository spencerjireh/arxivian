import clsx from 'clsx'

interface VerdictLineProps {
  verdict: string
  className?: string
}

/** The primary element on a card: what the paper is and what it takes to reproduce it. */
export default function VerdictLine({ verdict, className }: VerdictLineProps) {
  return (
    <p className={clsx('font-display text-lg text-stone-900 leading-snug', className)}>
      {verdict}
    </p>
  )
}

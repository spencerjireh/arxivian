// UI primitive: the centered loading spinner used by every page-level loading state.
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface SpinnerProps {
  /** Fill the viewport (the pre-Clerk boot screen) instead of a padded block. */
  fullScreen?: boolean
  className?: string
}

export default function Spinner({ fullScreen = false, className }: SpinnerProps) {
  return (
    <div
      className={clsx(
        'flex items-center justify-center',
        fullScreen ? 'h-screen' : 'py-24',
        className
      )}
    >
      <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
    </div>
  )
}

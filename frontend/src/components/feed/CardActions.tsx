import { Bookmark, BookmarkCheck, ExternalLink, Hammer, X } from 'lucide-react'
import Button from '../ui/Button'
import Chip from '../ui/Chip'
import type { PaperLifecycleState, PaperState } from '../../types/api'

export type PendingAction = PaperLifecycleState | 'clear' | null

export interface CardActionsProps {
  state: PaperState | null
  onSave: () => void
  onDismiss: () => void
  onImplementing: () => void
  pending?: PendingAction
  size?: 'sm' | 'md'
}

/** Save / Dismiss / Mark as Implementing. Dismiss is one click, no confirmation. */
export default function CardActions({
  state,
  onSave,
  onDismiss,
  onImplementing,
  pending = null,
  size = 'sm',
}: CardActionsProps) {
  const current = state?.state ?? null
  const iconClass = 'w-4 h-4'
  const isSaved = current === 'saved'
  const isImplementing = current === 'implementing'

  if (current === 'shipped') {
    return (
      <div className="flex items-center gap-2">
        <Chip tone="success" size="md">Shipped</Chip>
        {state?.repo_url && (
          <a
            href={state.repo_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-700"
          >
            Repo
            <ExternalLink className="w-3 h-3" strokeWidth={1.5} />
          </a>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <Button
        variant={isSaved ? 'secondary' : 'ghost'}
        size={size}
        onClick={onSave}
        isLoading={pending === 'saved' || (pending === 'clear' && isSaved)}
        aria-pressed={isSaved}
        leftIcon={
          isSaved ? (
            <BookmarkCheck className={iconClass} strokeWidth={1.5} />
          ) : (
            <Bookmark className={iconClass} strokeWidth={1.5} />
          )
        }
      >
        {isSaved ? 'Saved' : 'Save'}
      </Button>
      <Button
        variant={isImplementing ? 'secondary' : 'ghost'}
        size={size}
        onClick={onImplementing}
        isLoading={pending === 'implementing'}
        aria-pressed={isImplementing}
        leftIcon={<Hammer className={iconClass} strokeWidth={1.5} />}
      >
        {isImplementing ? 'Implementing' : 'Mark as Implementing'}
      </Button>
      <Button
        variant="ghost"
        size={size}
        onClick={onDismiss}
        isLoading={pending === 'dismissed'}
        leftIcon={<X className={iconClass} strokeWidth={1.5} />}
        aria-label="Dismiss"
      >
        Dismiss
      </Button>
    </div>
  )
}

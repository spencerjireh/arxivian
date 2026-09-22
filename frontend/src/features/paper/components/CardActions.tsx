// Feed card and paper header: Save / Dismiss (and optional Implementing / Ship) buttons with optimistic state.
import { useState } from 'react'
import { Bookmark, BookmarkCheck, ExternalLink, Hammer, Rocket, X } from 'lucide-react'
import Button from '@/components/ui/Button'
import Chip from '@/components/ui/Chip'
import Input from '@/components/ui/Input'
import type { PaperLifecycleState, PaperState } from '@/types/api'

export type PendingAction = PaperLifecycleState | 'clear' | null

export interface CardActionsProps {
  state: PaperState | null
  onSave: () => void
  onDismiss: () => void
  /** When set, the card offers "Mark as Implementing" (paper detail and Library; not the feed). */
  onImplementing?: () => void
  /** When set, an implementing paper gets a "Mark as shipped" action that asks for the repo. */
  onShip?: (repoUrl: string) => void
  pending?: PendingAction
  size?: 'sm' | 'md'
}

/** Save / Dismiss, plus Mark as Implementing / Mark as shipped where offered. Dismiss is one click, no confirmation. */
export default function CardActions({
  state,
  onSave,
  onDismiss,
  onImplementing,
  onShip,
  pending = null,
  size = 'sm',
}: CardActionsProps) {
  const current = state?.state ?? null
  const iconClass = 'w-4 h-4'
  const isSaved = current === 'saved'
  const isImplementing = current === 'implementing'
  const [shipOpen, setShipOpen] = useState(false)
  const [repoUrl, setRepoUrl] = useState('')

  if (current === 'shipped') {
    return (
      <div className="flex items-center gap-2">
        <Chip tone="success" size="md">
          Shipped
        </Chip>
        {state?.repo_url && (
          <a
            href={state.repo_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-xs text-stone-500 hover:text-stone-700"
          >
            Repo
            <ExternalLink className="h-3 w-3" strokeWidth={1.5} />
          </a>
        )}
      </div>
    )
  }

  const submitShip = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const url = repoUrl.trim()
    if (!url || !onShip) return
    onShip(url)
    setShipOpen(false)
    setRepoUrl('')
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {isImplementing && !onImplementing ? (
          // The feed offers no Implementing action: show the state instead of an unpressed
          // Save that would demote the paper on one click.
          <Chip tone="info" size="md">
            Implementing
          </Chip>
        ) : (
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
        )}
        {onImplementing && (
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
        )}
        {isImplementing && onShip && (
          <Button
            variant="ghost"
            size={size}
            onClick={() => setShipOpen((open) => !open)}
            isLoading={pending === 'shipped'}
            aria-expanded={shipOpen}
            leftIcon={<Rocket className={iconClass} strokeWidth={1.5} />}
          >
            Mark as shipped
          </Button>
        )}
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
      {shipOpen && (
        <form onSubmit={submitShip} className="flex items-end gap-2">
          <div className="max-w-md flex-1">
            <Input
              label="Repository URL"
              type="url"
              required
              autoFocus
              placeholder="https://github.com/you/repo"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="px-3 py-1.5"
            />
          </div>
          <Button type="submit" variant="primary" size={size}>
            Confirm
          </Button>
          <Button type="button" variant="ghost" size={size} onClick={() => setShipOpen(false)}>
            Cancel
          </Button>
        </form>
      )}
    </div>
  )
}

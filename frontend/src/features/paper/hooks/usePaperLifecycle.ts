// usePaperLifecycle: the Save / Dismiss / Implementing / Ship transitions for one paper, over
// the optimistic mutations in ../api/paper-state.ts. Lives in the component that renders the
// buttons, so pages carry no lifecycle state.
import { useClearPaperState, useSetPaperState } from '../api/paper-state'
import type { PaperLifecycleState, PaperState } from '@/types/api'

type PendingAction = PaperLifecycleState | 'clear' | null

export interface PaperLifecycle {
  /** The transition in flight for this paper, if any; drives the button spinners. */
  pending: PendingAction
  /** Saved -> cleared; anything else -> saved. */
  save: () => void
  dismiss: () => void
  /** Implementing -> saved; anything else -> implementing. */
  toggleImplementing: () => void
  ship: (repoUrl: string) => void
}

/**
 * Failures surface through the QueryClient's global mutation error toast, and the
 * optimistic cache updates roll back in the mutation's own onError, so callers never await.
 */
export function usePaperLifecycle(arxivId: string, state: PaperState | null): PaperLifecycle {
  const set = useSetPaperState()
  const clear = useClearPaperState()
  const current = state?.state ?? null

  const transition = (next: PaperLifecycleState, repoUrl?: string) =>
    set.mutate({ arxivId, body: repoUrl ? { state: next, repo_url: repoUrl } : { state: next } })

  return {
    pending: set.isPending ? (set.variables?.body.state ?? null) : clear.isPending ? 'clear' : null,
    save: () => (current === 'saved' ? clear.mutate({ arxivId }) : transition('saved')),
    dismiss: () => transition('dismissed'),
    toggleImplementing: () => transition(current === 'implementing' ? 'saved' : 'implementing'),
    ship: (repoUrl) => transition('shipped', repoUrl),
  }
}

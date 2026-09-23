// /library route: the caller's papers grouped Saved / Implementing / Shipped (GET /users/me/library).
import { useCallback, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, BookOpen, Loader2 } from 'lucide-react'
import { useLibrary } from '@/features/paper/api/get-library'
import { useClearPaperState, useSetPaperState } from '@/features/paper/api/paper-state'
import FeedList from '@/features/feed/components/FeedList'
import Chip from '@/components/ui/Chip'
import { getUserMessage } from '@/lib/errors'
import type { PendingAction } from '@/features/paper/components/CardActions'
import type { LibraryGroup, LibraryResponse, PaperLifecycleState } from '@/types/api'

const GROUPS: { key: LibraryGroup; label: string }[] = [
  { key: 'saved', label: 'Saved' },
  { key: 'implementing', label: 'Implementing' },
  { key: 'shipped', label: 'Shipped' },
]

const EMPTY: LibraryResponse = { saved: [], implementing: [], shipped: [] }

/** The return-visit surface: the caller's papers grouped saved -> implementing -> shipped. */
export default function LibraryPage() {
  const { data, isLoading, error } = useLibrary()
  const setState = useSetPaperState()
  const clearState = useClearPaperState()
  const [pending, setPending] = useState<{ arxivId: string; action: PendingAction } | null>(null)

  const library = data ?? EMPTY
  const total = GROUPS.reduce((n, g) => n + library[g.key].length, 0)

  const stateOf = useCallback(
    (arxivId: string) =>
      GROUPS.flatMap((g) => library[g.key]).find((i) => i.paper.arxiv_id === arxivId)?.state ??
      null,
    [library]
  )

  const run = useCallback((arxivId: string, action: PendingAction, fn: () => Promise<unknown>) => {
    setPending({ arxivId, action })
    void fn().finally(() => setPending((p) => (p?.arxivId === arxivId ? null : p)))
  }, [])

  const transition = useCallback(
    (arxivId: string, state: PaperLifecycleState, repo_url?: string) =>
      run(arxivId, state, () =>
        setState.mutateAsync({ arxivId, body: { state, repo_url } }).catch(() => undefined)
      ),
    [run, setState]
  )

  const onSave = useCallback(
    (arxivId: string) => {
      if (stateOf(arxivId)?.state === 'saved') {
        run(arxivId, 'clear', () => clearState.mutateAsync({ arxivId }).catch(() => undefined))
      } else {
        transition(arxivId, 'saved')
      }
    },
    [stateOf, run, clearState, transition]
  )
  const onDismiss = useCallback((arxivId: string) => transition(arxivId, 'dismissed'), [transition])
  const onImplementing = useCallback(
    (arxivId: string) =>
      transition(arxivId, stateOf(arxivId)?.state === 'implementing' ? 'saved' : 'implementing'),
    [stateOf, transition]
  )
  const onShip = useCallback(
    (arxivId: string, repoUrl: string) => transition(arxivId, 'shipped', repoUrl),
    [transition]
  )
  const pendingFor = useCallback(
    (arxivId: string): PendingAction => (pending?.arxivId === arxivId ? pending.action : null),
    [pending]
  )

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-10">
      <div className="pb-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-semibold text-stone-900">Library</h1>
          {data && (
            <span className="font-mono text-sm text-stone-400">
              {total} paper{total !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      <div>
        {isLoading ? (
          <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-error-soft)]">
              <AlertCircle className="h-5 w-5 text-[var(--color-error)]" strokeWidth={1.5} />
            </div>
            <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
          </div>
        ) : total === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-stone-100">
              <BookOpen className="h-5 w-5 text-stone-400" strokeWidth={1.5} />
            </div>
            <p className="text-sm font-medium text-stone-700">Nothing saved yet</p>
            <p className="mt-1 text-sm text-stone-400">
              Save a paper from the{' '}
              <Link to="/" className="text-stone-600 underline hover:text-stone-900">
                feed
              </Link>{' '}
              and it shows up here
            </p>
          </div>
        ) : (
          <div className="space-y-8">
            {GROUPS.filter((g) => library[g.key].length > 0).map((g) => (
              <section key={g.key} aria-labelledby={`library-${g.key}`}>
                <div className="mb-3 flex items-center gap-2">
                  <h2
                    id={`library-${g.key}`}
                    className="font-display text-lg font-semibold text-stone-900"
                  >
                    {g.label}
                  </h2>
                  <Chip>{library[g.key].length}</Chip>
                </div>
                <FeedList
                  items={library[g.key]}
                  signedIn
                  onSave={onSave}
                  onDismiss={onDismiss}
                  onImplementing={onImplementing}
                  onShip={onShip}
                  pendingFor={pendingFor}
                />
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

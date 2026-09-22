// /papers/:arxivId route (public): header, score breakdown, the scoped chat panel when signed
// in; polls the 202 only for a signed-in reader, shows the metadata preview otherwise.
import { useCallback, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { AlertCircle, Loader2 } from 'lucide-react'
import { usePaperScore } from '@/features/paper/api/get-paper-score'
import { useClearPaperState, useSetPaperState } from '@/features/paper/api/paper-state'
import ChatSignInPrompt from '@/features/paper/components/ChatSignInPrompt'
import PaperHeader from '@/features/paper/components/PaperHeader'
import PaperNotFound from '@/features/paper/components/PaperNotFound'
import PaperPreview from '@/features/paper/components/PaperPreview'
import PendingScoreState from '@/features/paper/components/PendingScoreState'
import ScoreBreakdown from '@/features/paper/components/ScoreBreakdown'
import ScopedChatPanel from '@/features/paper/components/ScopedChatPanel'
import { getUserMessage } from '@/lib/errors'
import type { PendingAction } from '@/features/paper/components/CardActions'
import type { PaperLifecycleState } from '@/types/api'

export default function PaperDetailPage() {
  const { arxivId = '' } = useParams<{ arxivId: string }>()
  const [search, setSearchParams] = useSearchParams()
  const chatSessionId = search.get('session')
  const setChatSession = useCallback(
    (sessionId: string | null) => {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev)
          if (sessionId) next.set('session', sessionId)
          else next.delete('session')
          return next
        },
        { replace: true }
      )
    },
    [setSearchParams]
  )
  const { isSignedIn } = useAuth()
  const signedIn = Boolean(isSignedIn)
  const { data, isLoading, error, pollTimedOut, restartPolling } = usePaperScore(arxivId, {
    poll: signedIn,
  })
  const setState = useSetPaperState()
  const clearState = useClearPaperState()
  const [pending, setPending] = useState<PendingAction>(null)

  const detail = data?.status === 'ready' ? data.detail : null
  const current = detail?.state?.state ?? null

  const run = useCallback((action: PendingAction, fn: () => Promise<unknown>) => {
    setPending(action)
    void fn().finally(() => setPending(null))
  }, [])
  const transition = useCallback(
    (state: PaperLifecycleState, repo_url?: string) =>
      run(state, () =>
        setState.mutateAsync({ arxivId, body: { state, repo_url } }).catch(() => undefined)
      ),
    [run, setState, arxivId]
  )
  const onSave = useCallback(() => {
    if (current === 'saved') {
      run('clear', () => clearState.mutateAsync({ arxivId }).catch(() => undefined))
    } else {
      transition('saved')
    }
  }, [current, run, clearState, arxivId, transition])
  const onDismiss = useCallback(() => transition('dismissed'), [transition])
  const onImplementing = useCallback(
    () => transition(current === 'implementing' ? 'saved' : 'implementing'),
    [current, transition]
  )
  const onShip = useCallback((repoUrl: string) => transition('shipped', repoUrl), [transition])

  let body: React.ReactNode
  if (isLoading) {
    body = (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-6 w-6 animate-spin text-stone-300" strokeWidth={1.5} />
      </div>
    )
  } else if (error?.status === 404 || error?.status === 400) {
    body = <PaperNotFound arxivId={arxivId} />
  } else if (error) {
    body = (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-error-soft)]">
          <AlertCircle className="h-5 w-5 text-[var(--color-error)]" strokeWidth={1.5} />
        </div>
        <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
      </div>
    )
  } else if (data?.status === 'pending' && !signedIn) {
    body = <PaperPreview paper={data.paper} />
  } else if (data?.status === 'pending' || !detail) {
    body = <PendingScoreState timedOut={pollTimedOut} onRetry={restartPolling} />
  } else {
    body = (
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-6">
          <PaperHeader
            paper={detail.paper}
            signedIn={signedIn}
            state={detail.state}
            onSave={onSave}
            onDismiss={onDismiss}
            onImplementing={onImplementing}
            onShip={onShip}
            pending={pending}
          />
          <ScoreBreakdown detail={detail} />
        </div>
        {signedIn ? (
          <ScopedChatPanel
            arxivId={arxivId}
            paperTitle={detail.paper.title}
            sessionId={chatSessionId}
            onSessionChange={setChatSession}
          />
        ) : (
          <ChatSignInPrompt />
        )}
      </div>
    )
  }

  return <div className="w-full">{body}</div>
}

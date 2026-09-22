// /papers/:arxivId route: header, score breakdown (polls the 202) and the scoped chat panel.
import { useCallback, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { usePaperScore } from '../api/scores'
import { useClearPaperState, useSetPaperState } from '../api/paperStates'
import AttributeChips from '../components/paper/AttributeChips'
import PaperHeader from '../components/paper/PaperHeader'
import PaperNotFound from '../components/paper/PaperNotFound'
import PendingScoreState from '../components/paper/PendingScoreState'
import ScoreBreakdown from '../components/paper/ScoreBreakdown'
import ScopedChatPanel from '../components/paper/ScopedChatPanel'
import { getUserMessage } from '../lib/errors'
import type { PendingAction } from '../components/feed/CardActions'
import type { PaperLifecycleState } from '../types/api'

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
  const { data, isLoading, error, pollTimedOut, restartPolling } = usePaperScore(arxivId)
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
  } else if (data?.status === 'pending' || !detail) {
    body = <PendingScoreState timedOut={pollTimedOut} onRetry={restartPolling} />
  } else {
    body = (
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-6">
          <PaperHeader
            paper={detail.paper}
            state={detail.state}
            onSave={onSave}
            onDismiss={onDismiss}
            onImplementing={onImplementing}
            onShip={onShip}
            pending={pending}
          />
          <AttributeChips attributes={detail.attributes} />
          <ScoreBreakdown detail={detail} />
        </div>
        <ScopedChatPanel
          arxivId={arxivId}
          paperTitle={detail.paper.title}
          sessionId={chatSessionId}
          onSessionChange={setChatSession}
        />
      </div>
    )
  }

  return <div className="w-full">{body}</div>
}

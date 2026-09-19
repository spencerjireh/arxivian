import { useCallback, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { AlertCircle, Loader2 } from 'lucide-react'
import { usePaperScore } from '../api/scores'
import { useClearPaperState, useSetPaperState } from '../api/paperState'
import type { PendingAction } from '../components/feed/CardActions'
import AttributeChips from '../components/paper/AttributeChips'
import PaperHeader from '../components/paper/PaperHeader'
import PaperNotFound from '../components/paper/PaperNotFound'
import PendingScoreState from '../components/paper/PendingScoreState'
import ScoreBreakdown from '../components/paper/ScoreBreakdown'
import ScopedChatPanel from '../components/paper/ScopedChatPanel'
import { getUserMessage } from '../lib/errors'
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
        { replace: true },
      )
    },
    [setSearchParams],
  )
  const { data, isLoading, error, pollTimedOut, restartPolling } = usePaperScore(arxivId)
  const setState = useSetPaperState()
  const clearState = useClearPaperState()
  const [pending, setPending] = useState<PendingAction>(null)

  const detail = data?.status === 'ready' ? data.detail : null
  const current = detail?.state?.state ?? null

  const run = useCallback((action: PendingAction, fn: () => Promise<unknown>) => {
    setPending(action)
    fn().finally(() => setPending(null))
  }, [])
  const transition = useCallback(
    (state: PaperLifecycleState) =>
      run(state, () => setState.mutateAsync({ arxivId, body: { state } }).catch(() => undefined)),
    [run, setState, arxivId],
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
    [current, transition],
  )

  let body: React.ReactNode
  if (isLoading) {
    body = (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin text-stone-300" strokeWidth={1.5} />
      </div>
    )
  } else if (error?.status === 404 || error?.status === 400) {
    body = <PaperNotFound arxivId={arxivId} />
  } else if (error) {
    body = (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="w-12 h-12 rounded-full bg-[var(--color-error-soft)] flex items-center justify-center mb-3">
          <AlertCircle className="w-5 h-5 text-[var(--color-error)]" strokeWidth={1.5} />
        </div>
        <p className="text-sm text-stone-500">{getUserMessage(error)}</p>
      </div>
    )
  } else if (data?.status === 'pending' || !detail) {
    body = <PendingScoreState timedOut={pollTimedOut} onRetry={restartPolling} />
  } else {
    body = (
      <div className="max-w-7xl mx-auto px-6 py-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="space-y-6 min-w-0">
          <PaperHeader
            paper={detail.paper}
            state={detail.state}
            onSave={onSave}
            onDismiss={onDismiss}
            onImplementing={onImplementing}
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

  return <div className="flex-1 overflow-y-auto">{body}</div>
}

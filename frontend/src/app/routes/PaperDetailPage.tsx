// /papers/:arxivId route (public): header, score breakdown, the scoped chat panel when signed
// in; polls the 202 only for a signed-in reader, shows the metadata preview otherwise.
import { useCallback } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { AlertCircle } from 'lucide-react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'
import Spinner from '@/components/ui/Spinner'
import StatusBlock from '@/components/ui/StatusBlock'
import { usePaperScore } from '@/features/paper/api/get-paper-score'
import ChatSignInPrompt from '@/features/paper/components/ChatSignInPrompt'
import PaperHeader from '@/features/paper/components/PaperHeader'
import PaperNotFound from '@/features/paper/components/PaperNotFound'
import PaperPreview from '@/features/paper/components/PaperPreview'
import PendingScoreState from '@/features/paper/components/PendingScoreState'
import ScopedChatPanel from '@/features/paper/components/ScopedChatPanel'
import ScoreBreakdown from '@/features/paper/components/ScoreBreakdown'
import { useSession } from '@/lib/auth'
import { getUserMessage } from '@/lib/errors'

function SectionFallback({ title }: { title: string }) {
  return <StatusBlock icon={AlertCircle} tone="error" title={title} />
}

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
  const { isSignedIn: signedIn } = useSession()
  const { data, isLoading, error, pollTimedOut, restartPolling } = usePaperScore(arxivId, {
    poll: signedIn,
  })

  const detail = data?.status === 'ready' ? data.detail : null

  let body: React.ReactNode
  if (isLoading) {
    body = <Spinner />
  } else if (error?.status === 404 || error?.status === 400) {
    body = <PaperNotFound arxivId={arxivId} />
  } else if (error) {
    body = <StatusBlock icon={AlertCircle} tone="error" title={getUserMessage(error)} />
  } else if (data?.status === 'pending' && !signedIn) {
    body = <PaperPreview paper={data.paper} />
  } else if (data?.status === 'pending' || !detail) {
    body = <PendingScoreState timedOut={pollTimedOut} onRetry={restartPolling} />
  } else {
    body = (
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-8 lg:grid-cols-[minmax(0,1fr)_400px]">
        <div className="min-w-0 space-y-6">
          <PaperHeader paper={detail.paper} signedIn={signedIn} state={detail.state} />
          <ErrorBoundary
            resetKey={arxivId}
            fallback={<SectionFallback title="The score breakdown failed to render" />}
          >
            <ScoreBreakdown detail={detail} />
          </ErrorBoundary>
        </div>
        {signedIn ? (
          <ErrorBoundary
            resetKey={arxivId}
            fallback={<SectionFallback title="The chat panel failed to render" />}
          >
            <ScopedChatPanel
              arxivId={arxivId}
              paperTitle={detail.paper.title}
              sessionId={chatSessionId}
              onSessionChange={setChatSession}
            />
          </ErrorBoundary>
        ) : (
          <ChatSignInPrompt />
        )}
      </div>
    )
  }

  return <div className="w-full">{body}</div>
}

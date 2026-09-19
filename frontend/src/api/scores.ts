// Paper score detail: GET /papers/{id}/score with 202 polling while scoring runs on demand.

import { useCallback, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiGet, ApiError } from './client'
import type { PaperScoreDetail, PaperScorePending, PaperScoreResult } from '../types/api'

export const SCORE_POLL_INTERVAL_MS = 5_000
export const SCORE_POLL_TIMEOUT_MS = 180_000

export const scoreKeys = {
  all: ['scores'] as const,
  details: () => [...scoreKeys.all, 'detail'] as const,
  detail: (arxivId: string) => [...scoreKeys.details(), arxivId] as const,
}

export async function fetchPaperScore(arxivId: string): Promise<PaperScoreResult> {
  const data = await apiGet<PaperScoreDetail | PaperScorePending>(
    `/papers/${encodeURIComponent(arxivId)}/score`,
  )
  if ('status' in data && data.status === 'pending') {
    return { status: 'pending', task_id: data.task_id }
  }
  return { status: 'ready', detail: data as PaperScoreDetail }
}

/**
 * The score breakdown for one paper. While the backend answers 202 the query refetches
 * every 5 s, for up to 3 minutes; `restartPolling` resets that budget.
 */
export function usePaperScore(arxivId: string | undefined) {
  const pendingSince = useRef<number | null>(null)
  const [pollTimedOut, setPollTimedOut] = useState(false)

  const query = useQuery<PaperScoreResult, ApiError>({
    queryKey: scoreKeys.detail(arxivId ?? ''),
    queryFn: () => fetchPaperScore(arxivId!),
    enabled: !!arxivId,
    staleTime: 5 * 60_000,
    retry: (count, err) => !(err instanceof ApiError && err.status === 404) && count < 1,
    refetchIntervalInBackground: false,
    refetchInterval: (q) => {
      const data = q.state.data
      if (!data || data.status !== 'pending') {
        pendingSince.current = null
        return false
      }
      const now = Date.now()
      if (pendingSince.current === null) pendingSince.current = now
      if (now - pendingSince.current >= SCORE_POLL_TIMEOUT_MS) {
        setPollTimedOut(true)
        return false
      }
      return SCORE_POLL_INTERVAL_MS
    },
  })

  const restartPolling = useCallback(() => {
    pendingSince.current = null
    setPollTimedOut(false)
    void query.refetch()
  }, [query])

  return { ...query, pollTimedOut, restartPolling }
}

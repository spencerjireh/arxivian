// Per-user paper lifecycle state: PUT / DELETE /papers/{id}/state with optimistic cache updates.

import { useMutation, useQueryClient, type InfiniteData, type QueryClient, type QueryKey } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiDelete, apiPut } from './client'
import { feedKeys } from './feed'
import { scoreKeys } from './scores'
import type { FeedParams, FeedResponse, PaperScoreResult, PaperState, SetPaperStateBody } from '../types/api'

type FeedData = InfiniteData<FeedResponse>

interface Snapshot {
  previousFeeds: [QueryKey, FeedData | undefined][]
  previousScore: PaperScoreResult | undefined
}

function feedParamsOf(key: QueryKey): FeedParams {
  const params = key[2]
  return params && typeof params === 'object' ? (params as FeedParams) : {}
}

/**
 * Apply a new state (or null) to every cached feed page. A dismissal removes the card from
 * caches that hide dismissed papers and decrements their totals.
 */
export function applyStateToCaches(
  queryClient: QueryClient,
  arxivId: string,
  nextState: PaperState | null,
): Snapshot {
  const previousFeeds = queryClient.getQueriesData<FeedData>({ queryKey: feedKeys.lists() })

  for (const [key, data] of previousFeeds) {
    if (!data) continue
    const hidesDismissed = !feedParamsOf(key).include_dismissed
    const removing = nextState?.state === 'dismissed' && hidesDismissed
    queryClient.setQueryData<FeedData>(key, {
      ...data,
      pages: data.pages.map((page) => {
        const present = page.items.some((item) => item.paper.arxiv_id === arxivId)
        if (!present) return page
        return {
          ...page,
          total: removing ? page.total - 1 : page.total,
          items: removing
            ? page.items.filter((item) => item.paper.arxiv_id !== arxivId)
            : page.items.map((item) =>
                item.paper.arxiv_id === arxivId ? { ...item, state: nextState } : item,
              ),
        }
      }),
    })
  }

  const scoreKey = scoreKeys.detail(arxivId)
  const previousScore = queryClient.getQueryData<PaperScoreResult>(scoreKey)
  if (previousScore?.status === 'ready') {
    queryClient.setQueryData<PaperScoreResult>(scoreKey, {
      status: 'ready',
      detail: { ...previousScore.detail, state: nextState },
    })
  }

  return { previousFeeds, previousScore }
}

function restore(queryClient: QueryClient, arxivId: string, snapshot?: Snapshot) {
  for (const [key, data] of snapshot?.previousFeeds ?? []) {
    queryClient.setQueryData(key, data)
  }
  if (snapshot?.previousScore) {
    queryClient.setQueryData(scoreKeys.detail(arxivId), snapshot.previousScore)
  }
}

interface SetPaperStateVariables {
  arxivId: string
  body: SetPaperStateBody
}

async function putPaperState({ arxivId, body }: SetPaperStateVariables): Promise<PaperState> {
  return apiPut<PaperState>(`/papers/${encodeURIComponent(arxivId)}/state`, body)
}

async function deletePaperState({ arxivId }: { arxivId: string }): Promise<void> {
  return apiDelete<void>(`/papers/${encodeURIComponent(arxivId)}/state`)
}

export function useSetPaperState() {
  const queryClient = useQueryClient()
  const clear = useClearPaperState()

  return useMutation({
    mutationFn: putPaperState,
    onMutate: async ({ arxivId, body }) => {
      await queryClient.cancelQueries({ queryKey: feedKeys.lists() })
      const optimistic: PaperState = {
        state: body.state,
        repo_url: body.repo_url ?? null,
        dismissal_reason: body.dismissal_reason ?? null,
        updated_at: new Date().toISOString(),
      }
      return applyStateToCaches(queryClient, arxivId, optimistic)
    },
    onError: (_err, { arxivId }, context) => {
      restore(queryClient, arxivId, context)
    },
    onSuccess: (_data, { arxivId, body }) => {
      if (body.state === 'dismissed') {
        toast('Dismissed', {
          action: { label: 'Undo', onClick: () => clear.mutate({ arxivId }) },
        })
      }
    },
    onSettled: (_data, _err, { arxivId }) => {
      queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
      queryClient.invalidateQueries({ queryKey: scoreKeys.detail(arxivId) })
    },
  })
}

export function useClearPaperState() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deletePaperState,
    onMutate: async ({ arxivId }) => {
      await queryClient.cancelQueries({ queryKey: feedKeys.lists() })
      return applyStateToCaches(queryClient, arxivId, null)
    },
    onError: (_err, { arxivId }, context) => {
      restore(queryClient, arxivId, context)
    },
    onSettled: (_data, _err, { arxivId }) => {
      queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
      queryClient.invalidateQueries({ queryKey: scoreKeys.detail(arxivId) })
    },
  })
}

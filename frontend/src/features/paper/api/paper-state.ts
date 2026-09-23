// Per-user paper lifecycle state: PUT / DELETE /papers/{id}/state with optimistic cache updates.

import {
  useMutation,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
  type QueryKey,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiDelete, apiPut } from '@/lib/api-client'
import { feedKeys, libraryKeys, scoreKeys } from '@/lib/query-keys'
import type {
  FeedParams,
  FeedResponse,
  LibraryGroup,
  LibraryResponse,
  PaperScoreResult,
  PaperState,
  SetPaperStateBody,
} from '@/types/api'

type FeedData = InfiniteData<FeedResponse>

interface Snapshot {
  previousFeeds: [QueryKey, FeedData | undefined][]
  previousScore: PaperScoreResult | undefined
  previousLibrary: LibraryResponse | undefined
}

const LIBRARY_GROUPS: LibraryGroup[] = ['saved', 'implementing', 'shipped']

/** Move the card to the group of its new state; a cleared or dismissed card leaves. */
function moveLibraryItem(
  library: LibraryResponse,
  arxivId: string,
  nextState: PaperState | null
): LibraryResponse {
  const current = LIBRARY_GROUPS.flatMap((g) => library[g]).find(
    (item) => item.paper.arxiv_id === arxivId
  )
  if (!current) return library
  const next: LibraryResponse = {
    saved: library.saved.filter((item) => item.paper.arxiv_id !== arxivId),
    implementing: library.implementing.filter((item) => item.paper.arxiv_id !== arxivId),
    shipped: library.shipped.filter((item) => item.paper.arxiv_id !== arxivId),
  }
  if (nextState && nextState.state !== 'dismissed') {
    next[nextState.state] = [{ ...current, state: nextState }, ...next[nextState.state]]
  }
  return next
}

function feedParamsOf(key: QueryKey): FeedParams {
  const params = key[2]
  return params && typeof params === 'object' ? params : {}
}

/**
 * Apply a new state (or null) to every cached feed page, the score detail and the library.
 * A dismissal removes the card from feed caches that hide dismissed papers (decrementing
 * their totals) and from the library.
 */
export function applyStateToCaches(
  queryClient: QueryClient,
  arxivId: string,
  nextState: PaperState | null
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
                item.paper.arxiv_id === arxivId ? { ...item, state: nextState } : item
              ),
        }
      }),
    })
  }

  const scoreKey = scoreKeys.detail(arxivId)
  const previousScore = queryClient.getQueryData<PaperScoreResult>(scoreKey)
  if (previousScore?.status === 'ready') {
    const next: PaperScoreResult = {
      status: 'ready',
      detail: { ...previousScore.detail, state: nextState },
    }
    queryClient.setQueryData<PaperScoreResult>(scoreKey, next)
  }

  const previousLibrary = queryClient.getQueryData<LibraryResponse>(libraryKeys.all)
  if (previousLibrary) {
    queryClient.setQueryData(libraryKeys.all, moveLibraryItem(previousLibrary, arxivId, nextState))
  }

  return { previousFeeds, previousScore, previousLibrary }
}

function restore(queryClient: QueryClient, arxivId: string, snapshot?: Snapshot) {
  for (const [key, data] of snapshot?.previousFeeds ?? []) {
    queryClient.setQueryData(key, data)
  }
  if (snapshot?.previousScore) {
    queryClient.setQueryData(scoreKeys.detail(arxivId), snapshot.previousScore)
  }
  if (snapshot?.previousLibrary) {
    queryClient.setQueryData(libraryKeys.all, snapshot.previousLibrary)
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
      await queryClient.cancelQueries({ queryKey: libraryKeys.all })
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
      void queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
      void queryClient.invalidateQueries({ queryKey: scoreKeys.detail(arxivId) })
      void queryClient.invalidateQueries({ queryKey: libraryKeys.all })
    },
  })
}

export function useClearPaperState() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deletePaperState,
    onMutate: async ({ arxivId }) => {
      await queryClient.cancelQueries({ queryKey: feedKeys.lists() })
      await queryClient.cancelQueries({ queryKey: libraryKeys.all })
      return applyStateToCaches(queryClient, arxivId, null)
    },
    onError: (_err, { arxivId }, context) => {
      restore(queryClient, arxivId, context)
    },
    onSettled: (_data, _err, { arxivId }) => {
      void queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
      void queryClient.invalidateQueries({ queryKey: scoreKeys.detail(arxivId) })
      void queryClient.invalidateQueries({ queryKey: libraryKeys.all })
    },
  })
}

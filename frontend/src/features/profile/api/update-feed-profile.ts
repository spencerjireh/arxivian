// Users REST API: PATCH /users/me/preferences with the onboarding feed profile.

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiPatch } from '@/lib/api-client'
import { meKeys } from '@/lib/auth'
import { feedKeys } from '@/lib/query-keys'
import type { FeedProfileInput, MeResponse } from '@/types/api'

async function patchFeedProfile(profile: FeedProfileInput): Promise<MeResponse> {
  return apiPatch<MeResponse>('/users/me/preferences', profile)
}

/** Saves the profile, writes the returned `me` into the cache, and invalidates the feed (ranking changes). */
export function useUpdateFeedProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: patchFeedProfile,
    onSuccess: (me) => {
      queryClient.setQueryData<MeResponse>(meKeys.me(), { ...me, onboarded: true })
      void queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
    },
  })
}

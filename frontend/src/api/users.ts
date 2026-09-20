// Users REST API: the onboarding feed profile (SPE-273)

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiPatch } from './client'
import { feedKeys } from './feed'
import { useUserStore } from '../stores/userStore'
import type { FeedProfileInput, MeResponse } from '../types/api'

async function patchFeedProfile(profile: FeedProfileInput): Promise<MeResponse> {
  return apiPatch<MeResponse>('/users/me/preferences', profile)
}

/** Saves the profile, refreshes the user store, and invalidates the feed (ranking changes). */
export function useUpdateFeedProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: patchFeedProfile,
    onSuccess: (me) => {
      useUserStore.getState().setMe({ ...me, onboarded: true })
      void queryClient.invalidateQueries({ queryKey: feedKeys.lists() })
    },
  })
}

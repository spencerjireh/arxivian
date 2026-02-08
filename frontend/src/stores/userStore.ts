// Zustand store for authenticated user tier and usage info

import { create } from 'zustand'
import { apiGet } from '../api/client'
import type { MeResponse } from '../types/api'

export interface UserState {
  me: MeResponse | null
  loading: boolean
  error: string | null

  fetchMe: () => Promise<void>
  clear: () => void
}

export const useUserStore = create<UserState>()((set) => ({
  me: null,
  loading: false,
  error: null,

  fetchMe: async () => {
    set({ loading: true, error: null })
    try {
      const data = await apiGet<MeResponse>('/v1/users/me')
      set({ me: data, loading: false })
    } catch {
      set({ loading: false, error: 'Failed to load user info' })
    }
  },

  clear: () => set({ me: null, loading: false, error: null }),
}))

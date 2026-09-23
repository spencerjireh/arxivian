// The one wrapper over Clerk plus the `me` query (GET /users/me): `useSession()` is what pages
// and features read; only features/auth (AuthSession, ProtectedRoute, OAuthButtons) touches
// Clerk directly.
import { useAuth, useClerk, useUser } from '@clerk/clerk-react'
import { queryOptions, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiGet } from './api-client'
import type { MeResponse } from '../types/api'

export const meKeys = {
  all: ['users'] as const,
  me: () => [...meKeys.all, 'me'] as const,
}

export function meQueryOptions(enabled: boolean) {
  return queryOptions({
    queryKey: meKeys.me(),
    queryFn: () => apiGet<MeResponse>('/users/me'),
    enabled,
    staleTime: 60_000,
  })
}

/** The signed-in caller's tier, usage and preferences; disabled (and undefined) when signed out. */
export function useMe() {
  const { isSignedIn } = useAuth()
  return useQuery(meQueryOptions(Boolean(isSignedIn)))
}

type ClerkUser = NonNullable<ReturnType<typeof useUser>['user']>

export interface Session {
  isLoaded: boolean
  isSignedIn: boolean
  /** Null while loading or signed out, so a stale `me` never renders after sign-out. */
  me: MeResponse | null
  /** Clerk's user record (name, avatar, created date, delete()); null when signed out. */
  user: ClerkUser | null
  signOut: () => Promise<void>
}

export function useSession(): Session {
  const { isLoaded, isSignedIn } = useAuth()
  const { user } = useUser()
  const clerk = useClerk()
  const queryClient = useQueryClient()
  const signedIn = Boolean(isSignedIn)
  const { data } = useQuery(meQueryOptions(signedIn))

  return {
    isLoaded,
    isSignedIn: signedIn,
    me: signedIn ? (data ?? null) : null,
    user: signedIn ? (user ?? null) : null,
    signOut: async () => {
      queryClient.removeQueries({ queryKey: meKeys.all })
      await clerk.signOut()
    },
  }
}

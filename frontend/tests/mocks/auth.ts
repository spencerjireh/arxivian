// Module-level mock for @/lib/auth: a mutable session that tests set per case.
import { mockUser } from './clerk'
import type { Session } from '@/lib/auth'
import type { MeResponse } from '@/types/api'

export const meKeys = {
  all: ['users'] as const,
  me: () => ['users', 'me'] as const,
}

export function makeMe(overrides: Partial<MeResponse> = {}): MeResponse {
  return {
    id: 'u',
    email: null,
    first_name: null,
    last_name: null,
    tier: 'free',
    daily_chat_limit: 10,
    chats_used_today: 0,
    preferences: { feed_profile: null },
    onboarded: false,
    ...overrides,
  }
}

export const mockSession: Session = {
  isLoaded: true,
  isSignedIn: false,
  me: null,
  user: mockUser as unknown as Session['user'],
  signOut: vi.fn().mockResolvedValue(undefined),
}

/** Reset between tests: signed out, no me. */
export function resetSession(): void {
  mockSession.isSignedIn = false
  mockSession.me = null
  vi.mocked(mockSession.signOut).mockClear()
}

export const useSession = () => mockSession
export const useMe = () => ({ data: mockSession.me ?? undefined })

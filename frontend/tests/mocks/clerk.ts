// Module-level mock for @clerk/clerk-react

import type { ReactNode } from 'react'

export const mockAuth = {
  isSignedIn: false,
  userId: 'user_test123',
  isLoaded: true,
  sessionId: 'sess_test',
  getToken: vi.fn().mockResolvedValue('mock-token'),
}

export const mockUser = {
  fullName: 'Test User',
  primaryEmailAddress: { emailAddress: 'test@example.com' },
  imageUrl: 'https://example.com/avatar.png',
  createdAt: new Date('2025-01-01').getTime(),
  delete: vi.fn().mockResolvedValue(undefined),
}

export const mockClerk = {
  signOut: vi.fn().mockResolvedValue(undefined),
}

export const useAuth = () => mockAuth
export const useUser = () => ({ user: mockUser, isLoaded: true })
export const useClerk = () => mockClerk

export function ClerkProvider({ children }: { children: ReactNode }) {
  return children
}

export function SignedIn({ children }: { children: ReactNode }) {
  return mockAuth.isSignedIn ? children : null
}

export function SignedOut({ children }: { children: ReactNode }) {
  return mockAuth.isSignedIn ? null : children
}

export function AuthenticateWithRedirectCallback() {
  return null
}

// Zustand sidebar state store
// Manages sidebar visibility with localStorage persistence

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SidebarState {
  isOpen: boolean
  lastSessionId: string | null
  toggle: () => void
  open: () => void
  close: () => void
  setLastSessionId: (id: string | null) => void
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isOpen: true,
      lastSessionId: null,

      toggle: () => set((state) => ({ isOpen: !state.isOpen })),
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
      setLastSessionId: (id: string | null) => set({ lastSessionId: id }),
    }),
    {
      name: 'sidebar-state',
    }
  )
)

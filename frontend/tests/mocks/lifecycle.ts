// Module-level mock for @/features/paper/hooks/usePaperLifecycle: one shared lifecycle whose
// actions are spies, so card and page tests assert the click wiring only.
import type { PaperLifecycle } from '@/features/paper/hooks/usePaperLifecycle'
import type { PaperState } from '@/types/api'

export const lifecycle = {
  pending: null as PaperLifecycle['pending'],
  save: vi.fn(),
  dismiss: vi.fn(),
  toggleImplementing: vi.fn(),
  ship: vi.fn(),
}

export const usePaperLifecycle = vi.fn<
  (arxivId: string, state: PaperState | null) => PaperLifecycle
>(() => lifecycle)

export function resetLifecycle(): void {
  lifecycle.pending = null
  lifecycle.save.mockClear()
  lifecycle.dismiss.mockClear()
  lifecycle.toggleImplementing.mockClear()
  lifecycle.ship.mockClear()
  usePaperLifecycle.mockClear()
}

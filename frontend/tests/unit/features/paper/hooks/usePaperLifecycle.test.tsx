import { renderHook } from '@testing-library/react'
import { usePaperLifecycle } from '@/features/paper/hooks/usePaperLifecycle'
import type { PaperState } from '@/types/api'

const set = { mutate: vi.fn(), isPending: false, variables: undefined as unknown }
const clear = { mutate: vi.fn(), isPending: false }
vi.mock('@/features/paper/api/paper-state', () => ({
  useSetPaperState: () => set,
  useClearPaperState: () => clear,
}))

function state(s: PaperState['state']): PaperState {
  return { state: s, repo_url: null, dismissal_reason: null, updated_at: 'x' }
}

beforeEach(() => {
  set.mutate.mockClear()
  set.isPending = false
  set.variables = undefined
  clear.mutate.mockClear()
  clear.isPending = false
})

describe('usePaperLifecycle', () => {
  it('save on an unsaved paper sets saved; save on a saved paper clears', () => {
    renderHook(() => usePaperLifecycle('a', null)).result.current.save()
    expect(set.mutate).toHaveBeenCalledWith({ arxivId: 'a', body: { state: 'saved' } })

    renderHook(() => usePaperLifecycle('a', state('saved'))).result.current.save()
    expect(clear.mutate).toHaveBeenCalledWith({ arxivId: 'a' })
  })

  it('dismiss is one PUT with no confirmation', () => {
    renderHook(() => usePaperLifecycle('a', state('saved'))).result.current.dismiss()
    expect(set.mutate).toHaveBeenCalledWith({ arxivId: 'a', body: { state: 'dismissed' } })
  })

  it('toggleImplementing moves saved -> implementing and implementing -> saved', () => {
    renderHook(() => usePaperLifecycle('a', state('saved'))).result.current.toggleImplementing()
    expect(set.mutate).toHaveBeenLastCalledWith({ arxivId: 'a', body: { state: 'implementing' } })

    renderHook(() =>
      usePaperLifecycle('a', state('implementing'))
    ).result.current.toggleImplementing()
    expect(set.mutate).toHaveBeenLastCalledWith({ arxivId: 'a', body: { state: 'saved' } })
  })

  it('ship sends the repo url', () => {
    renderHook(() => usePaperLifecycle('a', state('implementing'))).result.current.ship(
      'https://github.com/x/y'
    )
    expect(set.mutate).toHaveBeenCalledWith({
      arxivId: 'a',
      body: { state: 'shipped', repo_url: 'https://github.com/x/y' },
    })
  })

  it('pending reflects the transition in flight', () => {
    expect(renderHook(() => usePaperLifecycle('a', null)).result.current.pending).toBeNull()

    set.isPending = true
    set.variables = { arxivId: 'a', body: { state: 'dismissed' } }
    expect(renderHook(() => usePaperLifecycle('a', null)).result.current.pending).toBe('dismissed')

    set.isPending = false
    clear.isPending = true
    expect(renderHook(() => usePaperLifecycle('a', state('saved'))).result.current.pending).toBe(
      'clear'
    )
  })
})

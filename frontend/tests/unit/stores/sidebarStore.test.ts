import { useSidebarStore } from '../../../src/stores/sidebarStore'

describe('sidebarStore', () => {
  beforeEach(() => {
    useSidebarStore.setState({ isOpen: true })
  })

  it('defaults to isOpen: true', () => {
    expect(useSidebarStore.getState().isOpen).toBe(true)
  })

  it('toggle flips isOpen', () => {
    useSidebarStore.getState().toggle()
    expect(useSidebarStore.getState().isOpen).toBe(false)

    useSidebarStore.getState().toggle()
    expect(useSidebarStore.getState().isOpen).toBe(true)
  })

  it('open sets isOpen to true', () => {
    useSidebarStore.setState({ isOpen: false })
    useSidebarStore.getState().open()
    expect(useSidebarStore.getState().isOpen).toBe(true)
  })

  it('close sets isOpen to false', () => {
    useSidebarStore.getState().close()
    expect(useSidebarStore.getState().isOpen).toBe(false)
  })
})

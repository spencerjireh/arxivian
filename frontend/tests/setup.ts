import '@testing-library/jest-dom/vitest'

// Provide a working localStorage for Zustand persist middleware in jsdom
const store: Record<string, string> = {}
const localStorageMock: Storage = {
  getItem: (key: string) => store[key] ?? null,
  setItem: (key: string, value: string) => { store[key] = value },
  removeItem: (key: string) => { delete store[key] },
  clear: () => { for (const key in store) delete store[key] },
  get length() { return Object.keys(store).length },
  key: (index: number) => Object.keys(store)[index] ?? null,
}

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

// Provide document.fonts for EquationConstellation in jsdom
Object.defineProperty(document, 'fonts', {
  value: { ready: Promise.resolve() },
})

// Provide ResizeObserver for EquationConstellation in jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

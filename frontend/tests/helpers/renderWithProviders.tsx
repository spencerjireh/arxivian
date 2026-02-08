// Render helper wrapping components in QueryClientProvider + MemoryRouter

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import type { RenderOptions } from '@testing-library/react'

interface ProviderOptions {
  initialEntries?: string[]
}

export function renderWithProviders(
  ui: ReactNode,
  options: ProviderOptions & Omit<RenderOptions, 'wrapper'> = {},
) {
  const { initialEntries = ['/'], ...renderOptions } = options

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  })

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    )
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  }
}

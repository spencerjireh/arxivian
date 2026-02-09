import { render, screen, fireEvent } from '@testing-library/react'

import ErrorBoundary from '../../../../src/components/ui/ErrorBoundary'

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('test error')
  return <p>child content</p>
}

describe('ErrorBoundary', () => {
  beforeEach(() => {
    // Suppress React error boundary console.error noise
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary fallback={<p>fallback</p>}>
        <ThrowingChild shouldThrow={false} />
      </ErrorBoundary>
    )

    expect(screen.getByText('child content')).toBeInTheDocument()
    expect(screen.queryByText('fallback')).not.toBeInTheDocument()
  })

  it('renders fallback when child throws', () => {
    render(
      <ErrorBoundary fallback={<p>something went wrong</p>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('something went wrong')).toBeInTheDocument()
    expect(screen.queryByText('child content')).not.toBeInTheDocument()
  })

  it('calls render-prop fallback with error and reset function', () => {
    render(
      <ErrorBoundary fallback={({ error, resetErrorBoundary }) => (
        <div>
          <p>{error.message}</p>
          <button onClick={resetErrorBoundary}>reset</button>
        </div>
      )}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('test error')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'reset' })).toBeInTheDocument()
    fireEvent.click(screen.getByText('reset'))
  })

  it('calls componentDidCatch and logs the error', () => {
    const consoleSpy = vi.spyOn(console, 'error')

    render(
      <ErrorBoundary fallback={<p>fallback</p>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(consoleSpy).toHaveBeenCalledWith(
      'ErrorBoundary caught:',
      expect.any(Error),
      expect.any(String)
    )
  })
})

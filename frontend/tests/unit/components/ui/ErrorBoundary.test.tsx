import { render, screen, fireEvent } from '@testing-library/react'
import ErrorBoundary from '@/components/ui/ErrorBoundary'

const reportError = vi.fn()
vi.mock('@/lib/observability', () => ({
  reportError: (...args: unknown[]) => reportError(...args),
}))

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
      <ErrorBoundary
        fallback={({ error, resetErrorBoundary }) => (
          <div>
            <p>{error.message}</p>
            <button onClick={resetErrorBoundary}>reset</button>
          </div>
        )}
      >
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('test error')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'reset' })).toBeInTheDocument()
    fireEvent.click(screen.getByText('reset'))
  })

  it('reports the caught error with its component stack', () => {
    render(
      <ErrorBoundary fallback={<p>fallback</p>}>
        <ThrowingChild shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(reportError).toHaveBeenCalledWith(expect.any(Error), {
      componentStack: expect.any(String),
    })
  })
})

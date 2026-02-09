import { Component, type ReactNode } from 'react'

export interface FallbackProps {
  error: Error
  resetErrorBoundary: () => void
}

interface ErrorBoundaryProps {
  fallback?: ReactNode | ((props: FallbackProps) => ReactNode)
  onReset?: () => void
  resetKey?: string | number
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps): void {
    if (
      this.state.hasError &&
      prevProps.resetKey !== this.props.resetKey
    ) {
      this.resetErrorBoundary()
    }
  }

  resetErrorBoundary = (): void => {
    this.props.onReset?.()
    this.setState({ hasError: false, error: null })
  }

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      const { fallback } = this.props

      if (typeof fallback === 'function') {
        return fallback({
          error: this.state.error,
          resetErrorBoundary: this.resetErrorBoundary,
        })
      }

      if (fallback !== undefined) {
        return fallback
      }

      return (
        <div style={{ padding: '1rem', color: '#78716C' }}>
          <p>Something went wrong.</p>
        </div>
      )
    }

    return this.props.children
  }
}

import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import Button from '../ui/Button'

export default function PublicHeader() {
  const { isSignedIn } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="relative sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-stone-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="font-display text-xl font-semibold text-stone-900 tracking-tight">
          Arxivian
        </Link>
        <nav className="flex items-center gap-3">
          <Link
            to="/pricing"
            className={clsx(
              'text-sm transition-colors duration-150',
              pathname === '/pricing'
                ? 'text-stone-900 font-medium'
                : 'text-stone-600 hover:text-stone-900',
            )}
          >
            Pricing
          </Link>
          {isSignedIn ? (
            <Link to="/chat">
              <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" strokeWidth={2} />}>
                Go to Chat
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/sign-in">
                <Button variant="ghost" size="sm">Sign in</Button>
              </Link>
              <Link to="/sign-up">
                <Button variant="primary" size="sm">Get started</Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

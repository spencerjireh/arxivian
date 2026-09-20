import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { ArrowRight } from 'lucide-react'
import clsx from 'clsx'
import Button from '../ui/Button'
import logoIcon from '../../assets/logo-icon.png'

export default function PublicHeader() {
  const { isSignedIn } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="relative sticky top-0 z-50 border-b border-stone-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="font-display flex items-center gap-2 text-xl font-semibold tracking-tight text-stone-900"
        >
          <img
            src={logoIcon}
            alt=""
            className="h-6 w-auto"
            width={24}
            height={24}
            aria-hidden="true"
          />
          Arxivian
        </Link>
        <nav className="flex items-center gap-3">
          <Link
            to="/pricing"
            className={clsx(
              'text-sm transition-colors duration-150',
              pathname === '/pricing'
                ? 'font-medium text-stone-900'
                : 'text-stone-600 hover:text-stone-900'
            )}
          >
            Pricing
          </Link>
          {isSignedIn ? (
            <Link to="/feed">
              <Button
                variant="primary"
                size="sm"
                rightIcon={<ArrowRight className="h-3.5 w-3.5" strokeWidth={2} />}
              >
                Go to Chat
              </Button>
            </Link>
          ) : (
            <>
              <Link to="/sign-in">
                <Button variant="ghost" size="sm">
                  Sign in
                </Button>
              </Link>
              <Link to="/sign-up">
                <Button variant="primary" size="sm">
                  Get started
                </Button>
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

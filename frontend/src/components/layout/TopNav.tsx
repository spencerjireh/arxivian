// App shell: the one top nav for every visitor (Feed, About, Pricing; Library, Settings and
// the account menu when signed in; Sign in otherwise).
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import clsx from 'clsx'
import { matchesNav } from '@/lib/nav'
import SignInLink from '@/components/ui/SignInLink'
import logoIcon from '@/assets/logo-icon.png'
import UserMenu from './UserMenu'

const publicItems = [
  { path: '/', label: 'Feed' },
  { path: '/about', label: 'About' },
  { path: '/pricing', label: 'Pricing' },
] as const

const accountItems = [
  { path: '/library', label: 'Library' },
  { path: '/settings', label: 'Settings' },
] as const

export default function TopNav() {
  const { isSignedIn } = useAuth()
  const { pathname } = useLocation()
  const items = isSignedIn ? [...publicItems, ...accountItems] : publicItems

  return (
    <header className="sticky top-0 z-50 border-b border-stone-200 bg-white/95 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link
          to="/"
          className="font-display flex shrink-0 items-center gap-2 text-xl font-semibold tracking-tight text-stone-900"
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
        <nav aria-label="Primary" className="flex min-w-0 items-center gap-4 sm:gap-5">
          {items.map(({ path, label }) => {
            const active = matchesNav(path, pathname)
            return (
              <Link
                key={path}
                to={path}
                aria-current={active ? 'page' : undefined}
                className={clsx(
                  'text-sm transition-colors duration-150',
                  active ? 'font-medium text-stone-900' : 'text-stone-600 hover:text-stone-900'
                )}
              >
                {label}
              </Link>
            )
          })}
          {isSignedIn ? <UserMenu /> : <SignInLink variant="button">Sign in</SignInLink>}
        </nav>
      </div>
    </header>
  )
}

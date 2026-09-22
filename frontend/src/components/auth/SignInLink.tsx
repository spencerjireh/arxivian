// The one sign-in prompt: a link to /sign-in that remembers the current page as the return path.
import { Link, useLocation } from 'react-router-dom'
import clsx from 'clsx'

interface SignInLinkProps {
  variant?: 'button' | 'text'
  leftIcon?: React.ReactNode
  className?: string
  children: React.ReactNode
}

const variantClass = {
  button:
    'inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-700 transition-colors hover:border-stone-300 hover:bg-stone-50',
  text: 'inline-flex items-center gap-1.5 text-sm text-stone-600 transition-colors hover:text-stone-900',
}

export default function SignInLink({
  variant = 'text',
  leftIcon,
  className,
  children,
}: SignInLinkProps) {
  const location = useLocation()
  return (
    <Link
      to="/sign-in"
      state={{ from: location }}
      className={clsx(variantClass[variant], className)}
    >
      {leftIcon}
      {children}
    </Link>
  )
}

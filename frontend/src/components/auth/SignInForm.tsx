// Auth pages: sign-in form (OAuth) that forwards the return path to sign-up too.
import { Link } from 'react-router-dom'
import OAuthButtons from './OAuthButtons'

export default function SignInForm({ returnTo = '/' }: { returnTo?: string }) {
  return (
    <div className="animate-fade-in-up space-y-6">
      <OAuthButtons returnTo={returnTo} />

      <p className="text-center text-sm text-stone-500">
        Don't have an account?{' '}
        <Link
          to="/sign-up"
          state={{ from: returnTo }}
          className="font-medium text-stone-900 hover:text-stone-700"
        >
          Sign up
        </Link>
      </p>
    </div>
  )
}

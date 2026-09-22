// Auth pages: sign-up form (OAuth) that forwards the return path to sign-in too.
import { Link } from 'react-router-dom'
import OAuthButtons from './OAuthButtons'

export default function SignUpForm({ returnTo = '/' }: { returnTo?: string }) {
  return (
    <div className="animate-fade-in-up space-y-6">
      <OAuthButtons returnTo={returnTo} />

      <p className="text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link
          to="/sign-in"
          state={{ from: returnTo }}
          className="font-medium text-stone-900 hover:text-stone-700"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}

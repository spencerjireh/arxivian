import { Link } from 'react-router-dom'
import OAuthButtons from './OAuthButtons'

export default function SignUpForm() {
  return (
    <div className="space-y-6 animate-fade-in-up">
      <OAuthButtons />

      <p className="text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link
          to="/sign-in"
          className="font-medium text-stone-900 hover:text-stone-700"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}

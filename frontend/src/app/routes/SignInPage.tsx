// /sign-in route; returns to the page in location.state.from after sign-in.
import { useLocation } from 'react-router-dom'
import AuthLayout from '@/features/auth/components/AuthLayout'
import SignInForm from '@/features/auth/components/SignInForm'
import { returnPathFrom } from '@/lib/nav'

export default function SignInPage() {
  const returnTo = returnPathFrom(useLocation().state)
  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to save papers and chat with them">
      <SignInForm returnTo={returnTo} />
    </AuthLayout>
  )
}

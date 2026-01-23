import { SignIn } from '@clerk/clerk-react'
import AuthLayout from '../components/auth/AuthLayout'
import { clerkAppearance } from '../lib/clerkAppearance'

export default function SignInPage() {
  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue exploring AI research literature"
    >
      <SignIn
        routing="path"
        path="/sign-in"
        signUpUrl="/sign-up"
        afterSignInUrl="/"
        appearance={clerkAppearance}
      />
    </AuthLayout>
  )
}

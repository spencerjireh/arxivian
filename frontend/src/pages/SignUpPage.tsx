import { SignUp } from '@clerk/clerk-react'
import AuthLayout from '../components/auth/AuthLayout'
import { clerkAppearance } from '../lib/clerkAppearance'

export default function SignUpPage() {
  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start exploring AI research literature with Jireh's Agent"
    >
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        afterSignUpUrl="/"
        appearance={clerkAppearance}
      />
    </AuthLayout>
  )
}

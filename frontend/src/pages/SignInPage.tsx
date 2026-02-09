import AuthLayout from '../components/auth/AuthLayout'
import SignInForm from '../components/auth/SignInForm'

export default function SignInPage() {
  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue exploring academic research literature"
    >
      <SignInForm />
    </AuthLayout>
  )
}

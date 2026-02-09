import AuthLayout from '../components/auth/AuthLayout'
import SignUpForm from '../components/auth/SignUpForm'

export default function SignUpPage() {
  return (
    <AuthLayout
      title="Create an account"
      subtitle="Your AI-powered academic research workspace"
    >
      <SignUpForm />
    </AuthLayout>
  )
}

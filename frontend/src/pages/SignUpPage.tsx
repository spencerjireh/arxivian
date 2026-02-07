import AuthLayout from '../components/auth/AuthLayout'
import SignUpForm from '../components/auth/SignUpForm'

export default function SignUpPage() {
  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start exploring AI research literature with Arxivian"
    >
      <SignUpForm />
    </AuthLayout>
  )
}

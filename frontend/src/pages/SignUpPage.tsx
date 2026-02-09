import AuthLayout from '../components/auth/AuthLayout'
import SignUpForm from '../components/auth/SignUpForm'

export default function SignUpPage() {
  return (
    <AuthLayout
      title="Create an account"
      subtitle="Start exploring academic research literature with Arxivian"
    >
      <SignUpForm />
    </AuthLayout>
  )
}

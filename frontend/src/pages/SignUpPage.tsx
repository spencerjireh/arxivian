// /sign-up route.
import AuthLayout from '../components/auth/AuthLayout'
import SignUpForm from '../components/auth/SignUpForm'

export default function SignUpPage() {
  return (
    <AuthLayout title="Create an account" subtitle="Papers scored for implementability, every week">
      <SignUpForm />
    </AuthLayout>
  )
}

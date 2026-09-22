// /sign-up route; returns to the page in location.state.from after sign-up.
import { useLocation } from 'react-router-dom'
import AuthLayout from '../components/auth/AuthLayout'
import SignUpForm from '../components/auth/SignUpForm'
import { returnPathFrom } from '../lib/nav'

export default function SignUpPage() {
  const returnTo = returnPathFrom(useLocation().state)
  return (
    <AuthLayout title="Create an account" subtitle="Papers scored for implementability, every week">
      <SignUpForm returnTo={returnTo} />
    </AuthLayout>
  )
}

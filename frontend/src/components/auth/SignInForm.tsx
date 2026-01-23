import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import OAuthButtons from './OAuthButtons'

const fadeIn = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
}

export default function SignInForm() {
  return (
    <motion.div
      variants={fadeIn}
      initial="initial"
      animate="animate"
      className="space-y-6"
    >
      <OAuthButtons />

      <p className="text-center text-sm text-stone-500">
        Don't have an account?{' '}
        <Link
          to="/sign-up"
          className="font-medium text-stone-900 hover:text-stone-700"
        >
          Sign up
        </Link>
      </p>
    </motion.div>
  )
}

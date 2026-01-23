import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import OAuthButtons from './OAuthButtons'

const fadeIn = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
}

export default function SignUpForm() {
  return (
    <motion.div
      variants={fadeIn}
      initial="initial"
      animate="animate"
      className="space-y-6"
    >
      <OAuthButtons />

      <p className="text-center text-sm text-stone-500">
        Already have an account?{' '}
        <Link
          to="/sign-in"
          className="font-medium text-stone-900 hover:text-stone-700"
        >
          Sign in
        </Link>
      </p>
    </motion.div>
  )
}

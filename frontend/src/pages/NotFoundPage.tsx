import { useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { BookX } from 'lucide-react'
import { fadeInUp, transitions } from '../lib/animations'
import Button from '../components/ui/Button'

export default function NotFoundPage() {
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()

  const motionProps = shouldReduceMotion
    ? {}
    : { variants: fadeInUp, initial: 'initial', animate: 'animate', transition: transitions.base }

  return (
    <div className="min-h-screen bg-[var(--color-cream)] paper-grain flex items-center justify-center p-6">
      <motion.div
        className="relative z-10 max-w-md w-full bg-white rounded-xl border border-stone-200 shadow-md p-8 text-center"
        {...motionProps}
      >
        <p className="font-display text-7xl font-semibold text-stone-200 mb-4 select-none">
          404
        </p>

        <div className="w-12 h-12 rounded-full bg-stone-100 flex items-center justify-center mx-auto mb-5">
          <BookX className="w-5 h-5 text-stone-400" strokeWidth={1.5} />
        </div>

        <h1 className="font-display text-2xl font-semibold text-stone-900 mb-2">
          Page not found
        </h1>

        <div className="w-8 h-0.5 bg-[var(--color-accent)] mx-auto mb-4" />

        <p className="text-sm text-stone-500 leading-relaxed mb-6">
          The page you are looking for does not exist or has been moved.
        </p>

        <div className="flex items-center justify-center gap-3">
          <Button variant="primary" size="md" onClick={() => navigate(-1)}>
            Go back
          </Button>
          <Button variant="secondary" size="md" onClick={() => navigate('/')}>
            Return home
          </Button>
        </div>
      </motion.div>
    </div>
  )
}

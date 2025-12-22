import { useNavigate } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles, ArrowRight } from 'lucide-react'
import Button from '../ui/Button'
import { staggerContainer, staggerItem, transitions } from '../../lib/animations'

export default function WelcomeState() {
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()

  const handleNewConversation = () => {
    navigate('/new')
  }

  const containerVariants = shouldReduceMotion
    ? {}
    : {
        ...staggerContainer,
        animate: {
          ...staggerContainer.animate,
          transition: { staggerChildren: 0.1 },
        },
      }

  const itemVariants = shouldReduceMotion ? {} : staggerItem

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <motion.div
        className="max-w-lg text-center"
        variants={containerVariants}
        initial="initial"
        animate="animate"
      >
        <motion.div
          variants={itemVariants}
          transition={transitions.base}
          className="w-16 h-16 rounded-2xl bg-stone-900 flex items-center justify-center mx-auto mb-8 shadow-lg"
        >
          <Sparkles className="w-7 h-7 text-white" strokeWidth={1.5} />
        </motion.div>

        <motion.h1
          variants={itemVariants}
          transition={transitions.base}
          className="font-display text-4xl text-stone-900 mb-4 tracking-tight"
        >
          Welcome back
        </motion.h1>

        <motion.p
          variants={itemVariants}
          transition={transitions.base}
          className="text-stone-500 text-lg leading-relaxed mb-10"
        >
          Start a new conversation to explore academic research, get answers to complex questions, or discover new insights.
        </motion.p>

        <motion.div variants={itemVariants} transition={transitions.base}>
          <Button
            variant="primary"
            size="lg"
            onClick={handleNewConversation}
            rightIcon={<ArrowRight className="w-4 h-4" strokeWidth={2} />}
            className="shadow-md hover:shadow-lg"
          >
            Start a new conversation
          </Button>
        </motion.div>

        <motion.div
          variants={itemVariants}
          transition={transitions.base}
          className="mt-16 flex items-center justify-center gap-2"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-stone-200" />
          <div className="w-1.5 h-1.5 rounded-full bg-stone-300" />
          <div className="w-1.5 h-1.5 rounded-full bg-stone-200" />
        </motion.div>
      </motion.div>
    </div>
  )
}

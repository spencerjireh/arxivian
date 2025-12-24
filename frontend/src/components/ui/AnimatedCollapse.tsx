import { motion, AnimatePresence, useReducedMotion } from 'framer-motion'
import { transitions } from '../../lib/animations'

interface AnimatedCollapseProps {
  isOpen: boolean
  children: React.ReactNode
  className?: string
}

export function AnimatedCollapse({ isOpen, children, className }: AnimatedCollapseProps) {
  const shouldReduceMotion = useReducedMotion()

  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={shouldReduceMotion ? { duration: 0 } : transitions.base}
          style={{
            overflow: 'hidden',
            willChange: 'height, opacity',
            contain: 'layout style',
          }}
          className={className}
        >
          <div style={{ contain: 'layout' }}>{children}</div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

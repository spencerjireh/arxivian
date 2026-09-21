// Landing page: the ornamental rule between sections; `animated` draws the line on scroll.
import { motion, useReducedMotion } from 'framer-motion'

export default function SectionDivider({
  animated = false,
  className,
}: {
  animated?: boolean
  className?: string
}) {
  const shouldReduceMotion = useReducedMotion()

  if (!animated) {
    return (
      <div
        className={className ? `academic-divider ${className}` : 'academic-divider'}
        aria-hidden="true"
      >
        <div className="academic-divider-line" />
        <div className="academic-divider-diamond" />
      </div>
    )
  }

  return (
    <motion.div
      className="academic-divider relative z-10"
      aria-hidden="true"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={shouldReduceMotion ? { duration: 0 } : { duration: 0.6 }}
    >
      <motion.div
        className="academic-divider-line"
        initial={shouldReduceMotion ? undefined : { scaleX: 0 }}
        whileInView={shouldReduceMotion ? undefined : { scaleX: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: 'easeInOut' }}
        style={{ transformOrigin: 'center' }}
      />
      <div className="academic-divider-diamond" />
    </motion.div>
  )
}

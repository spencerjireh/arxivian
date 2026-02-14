import type { Variants, Transition } from 'framer-motion'

const ease = [0.25, 0.1, 0.25, 1] as const

export const transitions = {
  base: { duration: 0.3, ease } satisfies Transition,
  fast: { duration: 0.15, ease } satisfies Transition,
}

export const fadeIn: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 8 },
}

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
}

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
}

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
}

export const pulseVariants: Variants = {
  animate: {
    scale: [1, 1.15, 1],
    opacity: [1, 0.7, 1],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

export const scaleInStable: Variants = {
  initial: { scale: 0, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
}

export const cursorTransitionVariants: Variants = {
  streaming: {
    opacity: [1, 0],
    transition: {
      duration: 0.6,
      repeat: Infinity,
      repeatType: 'reverse',
      ease: 'easeInOut',
    },
  },
  complete: {
    opacity: 0,
    transition: { duration: 0.3 },
  },
}

import type { Variants, Transition } from 'framer-motion'

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
}

export const heroStaggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.12,
    },
  },
}

export const heroOrnamentLine: Variants = {
  initial: { scaleX: 0 },
  animate: { scaleX: 1 },
}

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

// -- Step icon running animations --

export const cursorTransitionVariants: Variants = {
  streaming: {
    opacity: [1, 0, 1],
    transition: {
      duration: 1,
      repeat: Infinity,
      times: [0, 0.5, 1],
    },
  },
  complete: {
    opacity: [1, 1, 0],
    transition: {
      duration: 0.4,
      times: [0, 0.25, 1],
      ease: 'easeOut',
    },
  },
}

// -- Sources reveal (post-stream fade-in + stagger) --

export const sourcesRevealContainer: Variants = {
  initial: { opacity: 0, y: 6 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.3,
      ease: [0.4, 0, 0.2, 1],
      staggerChildren: 0.06,
    },
  },
}

export const transitions = {
  fast: { duration: 0.15, ease: 'easeOut' } satisfies Transition,
  base: { duration: 0.2, ease: 'easeOut' } satisfies Transition,
  slow: { duration: 0.3, ease: [0.4, 0, 0.2, 1] } satisfies Transition,
  spring: { type: 'spring', stiffness: 400, damping: 30 } as Transition,
} as const

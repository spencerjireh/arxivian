import type { Variants, Transition } from 'framer-motion'

export const fadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
}

export const fadeInUp: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
}

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
    },
  },
}

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
}

export const pulseVariants: Variants = {
  animate: {
    opacity: [1, 0.5, 1],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
}

// -- Step icon running animations --

export const rockVariants: Variants = {
  animate: {
    rotate: [-12, 12, -12],
    transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
  },
}

export const bounceVariants: Variants = {
  animate: {
    y: [0, -3, 0],
    transition: { duration: 0.8, repeat: Infinity, ease: 'easeInOut' },
  },
}

export const nudgeVariants: Variants = {
  animate: {
    x: [0, 2, 0, -2, 0],
    transition: { duration: 0.9, repeat: Infinity, ease: 'easeInOut' },
  },
}

export const spinVariants: Variants = {
  animate: {
    rotate: 360,
    transition: { duration: 2, repeat: Infinity, ease: 'linear' },
  },
}

export const scalePulseVariants: Variants = {
  animate: {
    scale: [1, 0.82, 1],
    transition: { duration: 1, repeat: Infinity, ease: 'easeInOut' },
  },
}

export const completionPopVariants: Variants = {
  initial: { scale: 1 },
  animate: {
    scale: [1, 1.2, 1],
    transition: { duration: 0.2, ease: 'easeOut' },
  },
}

export const crossfadeStep: Variants = {
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -4 },
}

export const bgFadeIn: Variants = {
  initial: { opacity: 0 },
  animate: { opacity: 1, transition: { duration: 1, ease: 'easeOut' } },
}

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

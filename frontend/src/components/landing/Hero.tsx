// Landing hero: headline, subheadline, primary CTAs and the product mock.
import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { motion, useReducedMotion } from 'framer-motion'
import { ArrowRight, ChevronDown } from 'lucide-react'
import {
  staggerItem,
  heroStaggerContainer,
  heroOrnamentLine,
  transitions,
} from '../../lib/animations'
import Button from '../ui/Button'
import HeroArt from './HeroArt'
import ProductMock from './ProductMock'

export default function Hero() {
  const { isSignedIn } = useAuth()
  const shouldReduceMotion = useReducedMotion()

  return (
    <section className="relative flex flex-1 flex-col items-center justify-center px-4 py-24 sm:px-6 sm:py-32 lg:px-8">
      <div className="hero-vignette" aria-hidden="true" />
      <HeroArt className="hidden sm:block" />
      <motion.div
        className="relative z-10 mx-auto max-w-4xl text-center"
        variants={shouldReduceMotion ? undefined : heroStaggerContainer}
        initial="initial"
        animate="animate"
      >
        <div className="mx-auto max-w-3xl">
          <motion.div
            className="mx-auto mb-4 h-px w-20 bg-stone-300"
            variants={shouldReduceMotion ? undefined : heroOrnamentLine}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
            style={{ transformOrigin: 'center' }}
          />
          <motion.h1
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.slow}
            className="font-display letterpress mb-2 text-5xl leading-[1.1] tracking-tight text-stone-900 sm:text-6xl"
          >
            Papers you could
            <br />
            actually implement
          </motion.h1>
          <motion.div
            className="mx-auto mt-4 mb-6 h-px w-20 bg-stone-300"
            variants={shouldReduceMotion ? undefined : heroOrnamentLine}
            transition={{ duration: 0.6, ease: [0.4, 0, 0.2, 1] }}
            style={{ transformOrigin: 'center' }}
          />

          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.slow}
            className="mx-auto mb-10 max-w-2xl text-lg leading-relaxed text-stone-500 sm:text-xl"
          >
            Every week, new arXiv papers are scored on method clarity, resource feasibility, data
            availability and demand, ranked for your compute budget, and shown with the evidence
            behind each score.
          </motion.p>

          <motion.div
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.slow}
            className="flex flex-col items-center justify-center gap-3 sm:flex-row"
          >
            <Link to={isSignedIn ? '/feed' : '/sign-up'}>
              <Button
                variant="primary"
                size="lg"
                rightIcon={<ArrowRight className="h-4 w-4" strokeWidth={2} />}
              >
                {isSignedIn ? 'Open feed' : 'Get started'}
              </Button>
            </Link>
            {!isSignedIn && (
              <>
                <Link to="/pricing">
                  <Button variant="secondary" size="lg">
                    See plans
                  </Button>
                </Link>
                <button
                  onClick={() => {
                    document.getElementById('credibility')?.scrollIntoView({
                      behavior: shouldReduceMotion ? 'auto' : 'smooth',
                    })
                  }}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 text-sm text-stone-500 transition-colors duration-200 hover:text-stone-700"
                >
                  See how it works
                  <ChevronDown className="h-4 w-4" strokeWidth={1.5} />
                </button>
              </>
            )}
          </motion.div>
        </div>

        <motion.div
          variants={shouldReduceMotion ? undefined : staggerItem}
          transition={transitions.slow}
          className="mt-16 sm:mt-20"
        >
          <ProductMock />
        </motion.div>
      </motion.div>
    </section>
  )
}

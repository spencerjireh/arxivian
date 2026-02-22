import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { motion, useReducedMotion } from 'framer-motion'
import clsx from 'clsx'
import { Check, Mail } from 'lucide-react'
import { staggerContainer, staggerItem, transitions } from '../lib/animations'
import { useUserStore } from '../stores/userStore'
import Button from '../components/ui/Button'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

const tiers = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Get started with core research tools.',
    features: [
      '10 conversations per day',
      '5 paper ingests per day',
      'Default settings',
      'Paper library',
      'Hybrid search',
    ],
  },
  {
    name: 'Pro',
    price: '$0',
    period: 'during beta',
    description: 'Full access for power researchers.',
    features: [
      'Generous daily limits',
      'High-volume ingestion',
      'Custom model & settings',
      'Execution details',
      'Paper library',
      'Hybrid search',
      'Priority support',
    ],
    highlighted: true,
  },
] as const

const comparisonRows = [
  { feature: 'Daily conversations', free: '10', pro: 'Generous' },
  { feature: 'Daily paper ingests', free: '5', pro: 'Generous' },
  { feature: 'Settings', free: 'Default settings', pro: 'Custom model & settings' },
  { feature: 'Execution details', free: 'Hidden', pro: 'Full access' },
] as const

export default function PricingPage() {
  const { isSignedIn } = useAuth()
  const me = useUserStore((state) => state.me)
  const shouldReduceMotion = useReducedMotion()

  const userTier = me?.tier ?? 'free'

  return (
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col paper-grain">
      <PublicHeader />

      {/* Hero */}
      <section className="px-4 sm:px-6 lg:px-8 pt-20 pb-8 text-center">
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="text-sm text-stone-500 uppercase tracking-wider font-medium mb-4"
          >
            Pricing
          </motion.p>
          <motion.h1
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display text-4xl sm:text-5xl text-stone-900 tracking-tight mb-4"
          >
            Simple, transparent pricing
          </motion.h1>
          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="text-lg text-stone-500 max-w-xl mx-auto"
          >
            Pro access is free while we are in beta. No credit card required.
          </motion.p>
        </motion.div>
      </section>

      {/* Tier cards */}
      <section className="px-4 sm:px-6 lg:px-8 pb-16">
        <motion.div
          className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {tiers.map((tier) => {
            const isPro = tier.name === 'Pro'
            return (
              <motion.div
                key={tier.name}
                variants={shouldReduceMotion ? undefined : staggerItem}
                transition={transitions.base}
                className={clsx('bg-white border rounded-xl p-6 flex flex-col', isPro ? 'border-stone-900 ring-1 ring-stone-900' : 'border-stone-200')}
              >
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-display text-lg font-semibold text-stone-900">
                    {tier.name}
                  </h3>
                  {isPro && (
                    <span className="text-[10px] font-mono font-medium uppercase tracking-wider text-white bg-stone-900 px-1.5 py-0.5 rounded">
                      Beta
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-1 mb-1">
                  <span className="font-display text-3xl font-semibold text-stone-900">
                    {tier.price}
                  </span>
                  <span className="text-sm text-stone-400">/ {tier.period}</span>
                </div>
                <p className="text-sm text-stone-500 mb-6">{tier.description}</p>

                <ul className="space-y-2.5 mb-8 flex-1">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm text-stone-700">
                      <Check className="w-4 h-4 text-stone-400 shrink-0" strokeWidth={2} />
                      {feature}
                    </li>
                  ))}
                </ul>

                {isPro ? (
                  <a href="mailto:spencercebrian123@gmail.com?subject=Arxivian Pro Beta Access">
                    <Button variant="primary" size="md" className="w-full" leftIcon={<Mail className="w-4 h-4" strokeWidth={1.5} />}>
                      Contact us
                    </Button>
                  </a>
                ) : isSignedIn && userTier === 'free' ? (
                  <Button variant="secondary" size="md" className="w-full" disabled>
                    Current plan
                  </Button>
                ) : isSignedIn && userTier === 'pro' ? (
                  <Button variant="ghost" size="md" className="w-full text-stone-400" disabled>
                    --
                  </Button>
                ) : (
                  <Link to="/sign-up">
                    <Button variant="secondary" size="md" className="w-full">
                      Start for free
                    </Button>
                  </Link>
                )}
              </motion.div>
            )
          })}
        </motion.div>
      </section>

      {/* Comparison table */}
      <section className="px-4 sm:px-6 lg:px-8 pb-24">
        <motion.div
          className="max-w-2xl mx-auto"
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-40px' }}
        >
          <motion.h2
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display text-xl font-semibold text-stone-900 text-center mb-8"
          >
            Compare plans
          </motion.h2>

          <motion.div
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="bg-white border border-stone-200 rounded-xl overflow-hidden"
          >
            {/* Header */}
            <div className="grid grid-cols-3 border-b border-stone-100 px-5 py-3">
              <div className="text-sm font-medium text-stone-500">Feature</div>
              <div className="text-sm font-medium text-stone-500 text-center">Free</div>
              <div className="text-sm font-medium text-stone-900 text-center">Pro</div>
            </div>
            {/* Rows */}
            {comparisonRows.map((row, i) => (
              <div
                key={row.feature}
                className={clsx('grid grid-cols-3 px-5 py-3.5', i < comparisonRows.length - 1 && 'border-b border-stone-50')}
              >
                <div className="text-sm text-stone-700">{row.feature}</div>
                <div className="text-sm text-stone-500 text-center">{row.free}</div>
                <div className="text-sm text-stone-900 text-center">
                  {row.pro}
                </div>
              </div>
            ))}
          </motion.div>
        </motion.div>
      </section>

      <Footer />
    </div>
  )
}

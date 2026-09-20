import { Link } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import clsx from 'clsx'
import { Check, Mail } from 'lucide-react'
import { useUserStore } from '../stores/userStore'
import { useInView } from '../hooks/useInView'
import Button from '../components/ui/Button'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

const tiers = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'The weekly feed, scored and ranked for you.',
    features: [
      'Weekly implementability feed',
      'Per-dimension score breakdown',
      '10 paper chat turns per day',
      'Save, dismiss and track papers',
    ],
  },
  {
    name: 'Pro',
    price: '$0',
    period: 'during beta',
    description: 'For people who read a lot of papers.',
    features: ['Everything in Free', 'Unlimited paper chat turns', 'Priority support'],
    highlighted: true,
  },
] as const

const comparisonRows = [
  { feature: 'Weekly feed and score breakdown', free: 'Included', pro: 'Included' },
  { feature: 'Paper chat turns per day', free: '10', pro: 'Unlimited' },
  { feature: 'Support', free: 'Community', pro: 'Priority' },
] as const

export default function PricingPage() {
  const { isSignedIn } = useAuth()
  const me = useUserStore((state) => state.me)
  const [comparisonRef, comparisonInView] = useInView<HTMLDivElement>({
    once: true,
    margin: '-40px',
  })

  const userTier = me?.tier ?? 'free'

  return (
    <div className="paper-grain flex min-h-screen flex-col bg-[#FAFAF9]">
      <PublicHeader />

      {/* Hero */}
      <section className="px-4 pt-20 pb-8 text-center sm:px-6 lg:px-8">
        <div>
          <p
            style={{ '--stagger-index': 0 } as React.CSSProperties}
            className="animate-stagger mb-4 text-sm font-medium tracking-wider text-stone-500 uppercase"
          >
            Pricing
          </p>
          <h1
            style={{ '--stagger-index': 1 } as React.CSSProperties}
            className="font-display animate-stagger mb-4 text-4xl tracking-tight text-stone-900 sm:text-5xl"
          >
            Simple, transparent pricing
          </h1>
          <p
            style={{ '--stagger-index': 2 } as React.CSSProperties}
            className="animate-stagger mx-auto max-w-xl text-lg text-stone-500"
          >
            Pro access is free while we are in beta. No credit card required.
          </p>
        </div>
      </section>

      {/* Tier cards */}
      <section className="px-4 pb-16 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-3xl grid-cols-1 gap-6 md:grid-cols-2">
          {tiers.map((tier, index) => {
            const isPro = tier.name === 'Pro'
            return (
              <div
                key={tier.name}
                style={{ '--stagger-index': index + 3 } as React.CSSProperties}
                className={clsx(
                  'animate-stagger flex flex-col rounded-xl border bg-white p-6',
                  isPro ? 'border-stone-900 ring-1 ring-stone-900' : 'border-stone-200'
                )}
              >
                <div className="mb-1 flex items-center gap-2">
                  <h3 className="font-display text-lg font-semibold text-stone-900">{tier.name}</h3>
                  {isPro && (
                    <span className="rounded bg-stone-900 px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wider text-white uppercase">
                      Beta
                    </span>
                  )}
                </div>
                <div className="mb-1 flex items-baseline gap-1">
                  <span className="font-display text-3xl font-semibold text-stone-900">
                    {tier.price}
                  </span>
                  <span className="text-sm text-stone-400">/ {tier.period}</span>
                </div>
                <p className="mb-6 text-sm text-stone-500">{tier.description}</p>

                <ul className="mb-8 flex-1 space-y-2.5">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-2 text-sm text-stone-700">
                      <Check className="h-4 w-4 shrink-0 text-stone-400" strokeWidth={2} />
                      {feature}
                    </li>
                  ))}
                </ul>

                {isPro ? (
                  <a href="mailto:email@spencerjireh.com?subject=Arxivian Pro Beta Access">
                    <Button
                      variant="primary"
                      size="md"
                      className="w-full"
                      leftIcon={<Mail className="h-4 w-4" strokeWidth={1.5} />}
                    >
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
              </div>
            )
          })}
        </div>
      </section>

      {/* Comparison table */}
      <section className="px-4 pb-24 sm:px-6 lg:px-8">
        <div ref={comparisonRef} className="mx-auto max-w-2xl">
          <h2
            className={clsx(
              'font-display mb-8 text-center text-xl font-semibold text-stone-900',
              comparisonInView ? 'animate-fade-in-up' : 'opacity-0'
            )}
          >
            Compare plans
          </h2>

          <div
            className={clsx(
              'overflow-hidden rounded-xl border border-stone-200 bg-white',
              comparisonInView ? 'animate-fade-in-up' : 'opacity-0'
            )}
            style={comparisonInView ? { animationDelay: '50ms' } : undefined}
          >
            {/* Header */}
            <div className="grid grid-cols-3 border-b border-stone-100 px-5 py-3">
              <div className="text-sm font-medium text-stone-500">Feature</div>
              <div className="text-center text-sm font-medium text-stone-500">Free</div>
              <div className="text-center text-sm font-medium text-stone-900">Pro</div>
            </div>
            {/* Rows */}
            {comparisonRows.map((row, i) => (
              <div
                key={row.feature}
                className={clsx(
                  'grid grid-cols-3 px-5 py-3.5',
                  i < comparisonRows.length - 1 && 'border-b border-stone-50'
                )}
              >
                <div className="text-sm text-stone-700">{row.feature}</div>
                <div className="text-center text-sm text-stone-500">{row.free}</div>
                <div className="text-center text-sm text-stone-900">{row.pro}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

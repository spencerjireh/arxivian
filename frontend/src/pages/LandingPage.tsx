import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles, BookOpen, Search, Bell, ArrowRight } from 'lucide-react'
import { staggerContainer, staggerItem, transitions } from '../lib/animations'
import Button from '../components/ui/Button'
import Footer from '../components/layout/Footer'

const features = [
  {
    icon: Sparkles,
    title: 'Research Assistant',
    description:
      'Ask questions about papers and receive grounded answers with citations drawn directly from the literature.',
  },
  {
    icon: BookOpen,
    title: 'Paper Library',
    description:
      'Build a personal collection of arXiv papers, automatically processed and indexed for semantic retrieval.',
  },
  {
    icon: Search,
    title: 'Smart Search',
    description:
      'Hybrid search combining vector similarity and full-text matching to surface the most relevant passages.',
  },
  {
    icon: Bell,
    title: 'Automated Monitoring',
    description:
      'Configure saved searches to track new publications in your areas of interest, delivered on a daily schedule.',
  },
] as const

export default function LandingPage() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (isSignedIn) {
      navigate('/chat', { replace: true })
    }
  }, [isSignedIn, navigate])

  const getStaggerDelay = (index: number) => (shouldReduceMotion ? 0 : 0.08 * index)

  return (
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-stone-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="font-display text-xl font-semibold text-stone-900 tracking-tight">
            Arxivian
          </Link>
          <nav className="flex items-center gap-3">
            {isSignedIn ? (
              <Link to="/chat">
                <Button variant="primary" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" strokeWidth={2} />}>
                  Go to Chat
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/sign-in">
                  <Button variant="ghost" size="sm">Sign in</Button>
                </Link>
                <Link to="/sign-up">
                  <Button variant="primary" size="sm">Get started</Button>
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
        <div className="max-w-3xl mx-auto text-center">
          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...transitions.base, delay: getStaggerDelay(0) }}
            className="mb-6"
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 text-stone-600 text-xs font-medium tracking-wide uppercase">
              AI-powered research
            </span>
          </motion.div>

          <motion.h1
            initial={shouldReduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...transitions.base, delay: getStaggerDelay(1) }}
            className="font-display text-5xl sm:text-6xl text-stone-900 tracking-tight leading-[1.1] mb-6"
          >
            Navigate the arXiv
            <br />
            with clarity
          </motion.h1>

          <motion.p
            initial={shouldReduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...transitions.base, delay: getStaggerDelay(2) }}
            className="text-lg sm:text-xl text-stone-500 leading-relaxed mb-10 max-w-2xl mx-auto"
          >
            An intelligent research assistant that reads, indexes, and reasons over
            academic papers -- so you can focus on the ideas that matter.
          </motion.p>

          <motion.div
            initial={shouldReduceMotion ? false : { opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...transitions.base, delay: getStaggerDelay(3) }}
          >
            <Link to={isSignedIn ? '/chat' : '/sign-up'}>
              <Button
                variant="primary"
                size="lg"
                rightIcon={<ArrowRight className="w-4 h-4" strokeWidth={2} />}
              >
                {isSignedIn ? 'Open Chat' : 'Get started'}
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="px-4 sm:px-6 lg:px-8 pb-24 sm:pb-32">
        <motion.div
          className="max-w-6xl mx-auto"
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-80px' }}
        >
          <motion.h2
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display text-2xl sm:text-3xl text-stone-900 tracking-tight text-center mb-12"
          >
            Built for serious research
          </motion.h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {features.map(({ icon: Icon, title, description }) => (
              <motion.div
                key={title}
                variants={shouldReduceMotion ? undefined : staggerItem}
                transition={transitions.base}
                className="bg-white border border-stone-200 rounded-xl p-6"
              >
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-stone-700" strokeWidth={1.5} />
                </div>
                <h3 className="font-display text-lg font-semibold text-stone-900 mb-2">
                  {title}
                </h3>
                <p className="text-sm text-stone-500 leading-relaxed">
                  {description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      <Footer />
    </div>
  )
}

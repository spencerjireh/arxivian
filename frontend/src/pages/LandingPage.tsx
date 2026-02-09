import { useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { motion, useReducedMotion } from 'framer-motion'
import { Sparkles, BookOpen, Search, Bell, ArrowRight, ChevronDown, ChevronRight, User, FileText } from 'lucide-react'
import clsx from 'clsx'
import gsap from 'gsap'
import { useGSAP } from '@gsap/react'
import { SplitText } from 'gsap/SplitText'
import { ScrambleTextPlugin } from 'gsap/ScrambleTextPlugin'
import { staggerContainer, staggerItem, transitions } from '../lib/animations'
import Button from '../components/ui/Button'
import EquationConstellation from '../components/ui/EquationConstellation'
import Footer from '../components/layout/Footer'

gsap.registerPlugin(SplitText, ScrambleTextPlugin)

// -- Inline illustration components --

function ProductMock() {
  return (
    <div
      className="mock-window rounded-2xl shadow-lg border border-stone-200 bg-white overflow-hidden max-w-2xl mx-auto"
      style={{ perspective: '1200px', transform: 'rotateX(2deg) rotateY(-1deg)' }}
      aria-hidden="true"
    >
      {/* Window chrome */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-stone-100 bg-stone-50/60">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-stone-200" />
          <div className="w-2.5 h-2.5 rounded-full bg-stone-200" />
          <div className="w-2.5 h-2.5 rounded-full bg-stone-200" />
        </div>
        <div className="flex-1 flex justify-center">
          <span className="text-[11px] font-mono text-stone-400 bg-stone-100 px-3 py-0.5 rounded-md">
            arxivian.app/chat
          </span>
        </div>
      </div>

      {/* Chat content */}
      <div className="p-5 space-y-6">
        {/* User message */}
        <div className="flex justify-end">
          <div className="max-w-[80%]">
            <div className="flex items-center gap-2.5 mb-3 justify-end">
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-100">
                <User className="w-3.5 h-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </div>
            <div className="pr-9 text-right text-sm text-stone-800 leading-relaxed">
              What are the key contributions of attention mechanisms?
            </div>
          </div>
        </div>

        {/* Agent response */}
        <div>
          <div className="flex items-center gap-2.5 mb-3">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-900">
              <Sparkles className="w-3.5 h-3.5 text-white" strokeWidth={1.5} />
            </div>
            <span className="text-sm font-medium text-stone-500">Agent</span>
          </div>
          <div className="pl-9 space-y-4">
            <div className="text-sm text-stone-800 leading-relaxed">
              The <strong>self-attention mechanism</strong> allows models to weigh the
              relevance of each token relative to all others in a sequence, replacing recurrence entirely.
              This enables parallel computation and captures long-range dependencies more effectively.
            </div>

            {/* Sources section */}
            <div className="pt-4 border-t border-stone-100">
              <div className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-3">Sources</div>
              <div className="border border-stone-100 rounded-lg">
                <div className="px-4 py-3 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-stone-100 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-stone-500" strokeWidth={1.5} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-mono text-stone-400">1706.03762</span>
                      <span className="text-xs text-stone-300">|</span>
                      <span className="text-xs text-stone-400">96% match</span>
                    </div>
                    <p className="text-sm text-stone-700 leading-snug">Attention Is All You Need</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-stone-300 shrink-0 mt-1" strokeWidth={1.5} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ResearchAssistantIllustration() {
  return (
    <div className="bg-stone-50 rounded-lg p-3 space-y-3 text-xs">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[85%]">
          <div className="flex items-center gap-1.5 justify-end mb-1">
            <span className="text-[10px] font-medium text-stone-400">You</span>
            <div className="w-4 h-4 rounded bg-stone-200 flex items-center justify-center">
              <User className="w-2.5 h-2.5 text-stone-500" strokeWidth={1.5} />
            </div>
          </div>
          <div className="text-right text-stone-700 pr-5">How does RLHF improve alignment?</div>
        </div>
      </div>
      {/* Agent message */}
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <div className="w-4 h-4 rounded bg-stone-900 flex items-center justify-center">
            <Sparkles className="w-2.5 h-2.5 text-white" strokeWidth={1.5} />
          </div>
          <span className="text-[10px] font-medium text-stone-400">Agent</span>
        </div>
        <div className="pl-5 text-stone-600 leading-relaxed">
          <strong className="text-stone-800">RLHF</strong> fine-tunes language models using human preference rankings
          to better align outputs with user intent.
        </div>
      </div>
    </div>
  )
}

function PaperLibraryIllustration() {
  return (
    <div className="relative h-24">
      {[
        { id: '2312.00752', title: 'LLM Alignment Survey', opacity: 0.7, offset: 16 },
        { id: '2310.06825', title: 'Scaling Laws for LMs', opacity: 0.85, offset: 8 },
        { id: '2306.15595', title: 'Direct Preference Optimization', opacity: 1, offset: 0 },
      ].map((paper) => (
        <div
          key={paper.id}
          className="absolute left-0 right-0 bg-white border border-stone-200 rounded-lg px-3 py-2 flex items-center gap-2"
          style={{ opacity: paper.opacity, top: paper.offset }}
        >
          <FileText className="w-3.5 h-3.5 text-stone-400 shrink-0" strokeWidth={1.5} />
          <span className="text-[10px] font-mono text-stone-400">{paper.id}</span>
          <span className="text-xs text-stone-600 truncate">{paper.title}</span>
        </div>
      ))}
    </div>
  )
}

function SmartSearchIllustration() {
  return (
    <div className="space-y-2">
      {/* Retrieval pipeline */}
      <div className="flex items-center gap-1.5 text-[10px] text-stone-400">
        <Search className="w-3 h-3" strokeWidth={1.5} />
        <span>vector + full-text retrieval</span>
      </div>
      {/* Retrieved chunks */}
      <div className="space-y-1.5 text-[11px] text-stone-500 leading-relaxed">
        <div className="bg-white border border-stone-100 rounded px-2.5 py-1.5 flex items-center gap-2">
          <span className="text-amber-700 text-[10px] font-medium shrink-0">0.94</span>
          <span className="truncate">...self-attention mechanism allows the model to attend...</span>
        </div>
        <div className="bg-white border border-stone-100 rounded px-2.5 py-1.5 flex items-center gap-2">
          <span className="text-amber-700 text-[10px] font-medium shrink-0">0.87</span>
          <span className="truncate">...multi-head attention projects queries, keys, and values...</span>
        </div>
      </div>
    </div>
  )
}

function ScheduledIngestionIllustration() {
  return (
    <div className="space-y-2">
      {/* Schedule indicator */}
      <div className="flex items-center gap-2">
        <Bell className="w-4 h-4 text-stone-500" strokeWidth={1.5} />
        <span className="text-xs text-stone-500 font-medium">Daily at 2:00 AM UTC</span>
      </div>
      {/* Queued papers */}
      <div className="space-y-1.5">
        <div className="bg-white border border-stone-200 rounded-lg px-2.5 py-1.5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
          <div className="text-xs text-stone-600 truncate">+3 papers added to library</div>
        </div>
        <div className="bg-white border border-stone-200 rounded-lg px-2.5 py-1.5 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" />
          <div className="text-xs text-stone-600 truncate">+1 paper added to library</div>
        </div>
      </div>
    </div>
  )
}

function FeatureIllustration({ title }: { title: string }) {
  switch (title) {
    case 'Research Assistant':
      return <ResearchAssistantIllustration />
    case 'Paper Library':
      return <PaperLibraryIllustration />
    case 'Smart Search':
      return <SmartSearchIllustration />
    case 'Scheduled Ingestion':
      return <ScheduledIngestionIllustration />
    default:
      return null
  }
}

// -- Feature data --

const features = [
  {
    icon: Sparkles,
    title: 'Research Assistant',
    description:
      'Ask questions about papers and receive grounded answers with citations drawn directly from the literature.',
    size: 'large' as const,
  },
  {
    icon: BookOpen,
    title: 'Paper Library',
    description:
      'Build a personal collection of arXiv papers, automatically processed and indexed for semantic retrieval.',
    size: 'small' as const,
  },
  {
    icon: Search,
    title: 'Smart Search',
    description:
      'Answers are powered by hybrid retrieval -- vector similarity and full-text matching work together to find the most relevant passages.',
    size: 'small' as const,
  },
  {
    icon: Bell,
    title: 'Scheduled Ingestion',
    description:
      'Configure saved arXiv searches that run daily, automatically adding new papers to your library as they appear.',
    size: 'small' as const,
  },
]

export default function LandingPage() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()
  const heroRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isSignedIn) {
      navigate('/chat', { replace: true })
    }
  }, [isSignedIn, navigate])

  useGSAP(() => {
    if (shouldReduceMotion) return

    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })

    const split = new SplitText('.hero-heading', {
      type: 'words',
      autoSplit: true,
    })
    tl.from(split.words, {
      y: 40,
      opacity: 0,
      stagger: 0.06,
      duration: 0.8,
    })

    tl.to('.hero-badge-text', {
      scrambleText: {
        text: 'Research, accelerated',
        chars: 'arxiv0123456789',
        speed: 0.4,
        revealDelay: 0.3,
      },
      duration: 1.2,
    }, '<0.3')

    tl.from('.hero-description', {
      opacity: 0,
      y: 20,
      duration: 0.6,
    }, '-=0.4')

    tl.from('.hero-cta', {
      opacity: 0,
      y: 16,
      duration: 0.5,
    }, '-=0.2')

    tl.from('.hero-ornament-line', {
      scaleX: 0,
      duration: 0.6,
      ease: 'power2.inOut',
      stagger: 0.1,
    }, '-=0.4')

    tl.from('.hero-product-mock', {
      opacity: 0,
      y: 40,
      duration: 0.8,
      ease: 'power3.out',
    }, '-=0.3')
  }, { scope: heroRef })

  return (
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col paper-grain">
      {/* Navigation */}
      <header className="relative sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-stone-200">
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
      <section ref={heroRef} className="relative flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 py-24 sm:py-32">
        <div className="hero-vignette" aria-hidden="true" />
        <EquationConstellation className="hidden sm:block" />
        <div className="relative z-10 max-w-4xl mx-auto text-center">
          <div className="max-w-3xl mx-auto">
            <div className="mb-6">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 text-stone-600 text-xs font-medium tracking-wide uppercase">
                <span className="hero-badge-text">Research, accelerated</span>
              </span>
            </div>

            <div className="hero-ornament-line h-px w-20 bg-stone-300 mx-auto mb-4" />
            <h1 className="hero-heading font-display text-5xl sm:text-6xl text-stone-900 tracking-tight leading-[1.1] mb-2 letterpress">
              Navigate the arXiv
              <br />
              with clarity
            </h1>
            <div className="hero-ornament-line h-px w-20 bg-stone-300 mx-auto mt-4 mb-6" />

            <p className="hero-description text-lg sm:text-xl text-stone-500 leading-relaxed mb-10 max-w-2xl mx-auto">
              An intelligent research assistant that reads, indexes, and reasons over
              academic papers -- so you can focus on the ideas that matter.
            </p>

            <div className="hero-cta flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link to={isSignedIn ? '/chat' : '/sign-up'}>
                <Button
                  variant="primary"
                  size="lg"
                  rightIcon={<ArrowRight className="w-4 h-4" strokeWidth={2} />}
                >
                  {isSignedIn ? 'Open Chat' : 'Try a research question'}
                </Button>
              </Link>
              {!isSignedIn && (
                <button
                  onClick={() => {
                    document.getElementById('credibility')?.scrollIntoView({
                      behavior: shouldReduceMotion ? 'auto' : 'smooth',
                    })
                  }}
                  className="inline-flex items-center gap-1.5 text-sm text-stone-500 hover:text-stone-700 transition-colors duration-200 px-4 py-2.5"
                >
                  See how it works
                  <ChevronDown className="w-4 h-4" strokeWidth={1.5} />
                </button>
              )}
            </div>
          </div>

          <div className="hero-product-mock mt-16 sm:mt-20">
            <ProductMock />
          </div>
        </div>
      </section>

      {/* Academic divider */}
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

      {/* Features */}
      <section className="relative z-10 px-4 sm:px-6 lg:px-8 pt-16 sm:pt-20 pb-24 sm:pb-32 dot-grid">
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

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {features.map(({ icon: Icon, title, description, size }) => (
              <motion.div
                key={title}
                variants={shouldReduceMotion ? undefined : staggerItem}
                transition={transitions.base}
                whileHover={shouldReduceMotion ? undefined : { y: -4, transition: { duration: 0.2 } }}
                className={clsx(
                  'bg-white border border-stone-200 rounded-xl p-6 flex flex-col hover:border-stone-300 transition-colors duration-200',
                  size === 'large' && 'md:col-span-2 lg:col-span-2',
                )}
              >
                <div className="w-10 h-10 rounded-lg bg-stone-100 flex items-center justify-center mb-4">
                  <Icon className="w-5 h-5 text-stone-700" strokeWidth={1.5} />
                </div>
                <h3 className="font-display text-lg font-semibold text-stone-900 mb-2">
                  {title}
                </h3>
                <p className="text-sm text-stone-500 leading-relaxed mb-4">
                  {description}
                </p>
                <div className="mt-auto">
                  <FeatureIllustration title={title} />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Credibility */}
      <section id="credibility" className="relative z-10 bg-[#FAFAF9] px-4 sm:px-6 lg:px-8 pb-24 sm:pb-32">
        {/* Top divider */}
        <div className="academic-divider mb-16" aria-hidden="true">
          <div className="academic-divider-line" />
          <div className="academic-divider-diamond" />
        </div>

        <motion.div
          className="max-w-4xl mx-auto text-center"
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-80px' }}
        >
          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display text-2xl sm:text-3xl text-stone-900 tracking-tight mb-2"
          >
            Search and ingest from arXiv's{' '}
            <span className="text-stone-500">2,400,000+</span>{' '}
            paper catalog
          </motion.p>

          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="text-sm text-stone-400 mb-12"
          >
            See it in action
          </motion.p>

          {/* Sample Q&A card */}
          <motion.div
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="bg-white rounded-xl shadow-sm border border-stone-200 text-left max-w-2xl mx-auto"
          >
            {/* Question */}
            <div className="p-5">
              <div className="flex justify-end">
                <div className="max-w-[80%]">
                  <div className="flex items-center gap-2.5 justify-end mb-2">
                    <span className="text-sm font-medium text-stone-500">You</span>
                    <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-100">
                      <User className="w-3.5 h-3.5 text-stone-500" strokeWidth={1.5} />
                    </div>
                  </div>
                  <div className="pr-9 text-right text-sm text-stone-800 leading-relaxed">
                    Summarize the key findings of arXiv:2301.07041
                  </div>
                </div>
              </div>
            </div>

            <hr className="border-stone-100" />

            {/* Answer */}
            <div className="p-5">
              <div className="flex items-center gap-2.5 mb-2">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-stone-900">
                  <Sparkles className="w-3.5 h-3.5 text-white" strokeWidth={1.5} />
                </div>
                <span className="text-sm font-medium text-stone-500">Agent</span>
              </div>
              <div className="pl-9 text-sm text-stone-600 leading-relaxed space-y-2">
                <p>
                  The paper introduces <strong className="text-stone-800">Retrieval-Augmented Generation (RAG)</strong> as
                  a framework for grounding language model outputs in retrieved evidence, reducing
                  hallucination and improving factual accuracy across knowledge-intensive tasks.
                </p>
                <p>
                  Key findings include a 15% improvement in factual consistency over baseline models,
                  with the retrieval component enabling verifiable citations back to source documents.
                </p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </section>

      <Footer />
    </div>
  )
}

import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  Sparkles,
  BookOpen,
  Search,
  GitBranch,
  ArrowRight,
  ChevronDown,
  ChevronRight,
  User,
  FileText,
} from 'lucide-react'
import clsx from 'clsx'
import logoIcon from '../assets/logo-icon.png'
import {
  staggerContainer,
  staggerItem,
  heroStaggerContainer,
  heroOrnamentLine,
  transitions,
} from '../lib/animations'
import Button from '../components/ui/Button'
import HeroArt from '../components/landing/HeroArt'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

// -- Inline illustration components --

function ProductMock() {
  return (
    <div
      className="mock-window mx-auto max-w-2xl overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-lg"
      style={{ perspective: '1200px', transform: 'rotateX(2deg) rotateY(-1deg)' }}
      aria-hidden="true"
    >
      {/* Window chrome */}
      <div className="flex items-center gap-2 border-b border-stone-100 bg-stone-50/60 px-4 py-2.5">
        <div className="flex gap-1.5">
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
          <div className="h-2.5 w-2.5 rounded-full bg-stone-200" />
        </div>
        <div className="flex flex-1 justify-center">
          <span className="rounded-md bg-stone-100 px-3 py-0.5 font-mono text-[11px] text-stone-400">
            arxivian.app/chat
          </span>
        </div>
      </div>

      {/* Chat content */}
      <div className="space-y-6 p-5">
        {/* User message */}
        <div className="flex justify-end">
          <div className="max-w-[80%]">
            <div className="mb-3 flex items-center justify-end gap-2.5">
              <span className="text-sm font-medium text-stone-500">You</span>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                <User className="h-3.5 w-3.5 text-stone-500" strokeWidth={1.5} />
              </div>
            </div>
            <div className="pr-9 text-right text-sm leading-relaxed text-stone-800">
              What are the key contributions of attention mechanisms?
            </div>
          </div>
        </div>

        {/* Agent response */}
        <div>
          <div className="mb-3 flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
              <img src={logoIcon} alt="" className="h-4 w-4" aria-hidden="true" />
            </div>
            <span className="text-sm font-medium text-stone-500">Arxivian</span>
          </div>
          <div className="space-y-4 pl-9">
            {/* Reasoning bar (static mock of ThinkingTimeline collapsed state) */}
            <div className="flex items-center gap-2 border-l-2 border-stone-200 py-1.5 pl-3 text-xs text-stone-400">
              <BookOpen className="h-3.5 w-3.5 shrink-0" strokeWidth={1.5} />
              <span>View reasoning</span>
              <span className="ml-auto flex items-center gap-1.5">
                <span className="italic">Searched 1 source</span>
                <span className="font-mono">-- 2.1s</span>
                <ChevronRight className="h-3.5 w-3.5" strokeWidth={1.5} />
              </span>
            </div>

            <div className="text-sm leading-relaxed text-stone-800">
              The <strong>self-attention mechanism</strong> allows models to weigh the relevance of
              each token relative to all others in a sequence, replacing recurrence entirely. This
              enables parallel computation and captures long-range dependencies more effectively.
            </div>

            {/* Sources section */}
            <div className="border-t border-stone-100 pt-4">
              <div className="mb-3 text-xs font-medium tracking-wider text-stone-400 uppercase">
                Sources
              </div>
              <div className="rounded-lg border border-stone-100">
                <div className="flex items-start gap-3 px-4 py-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-stone-100">
                    <FileText className="h-4 w-4 text-stone-500" strokeWidth={1.5} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="font-mono text-xs text-stone-400">1706.03762</span>
                      <span className="text-xs text-stone-300">|</span>
                      <span className="text-xs text-stone-400">96% match</span>
                    </div>
                    <p className="text-sm leading-snug text-stone-700">Attention Is All You Need</p>
                    <div className="mt-1.5 h-1 w-20 overflow-hidden rounded-full bg-stone-100">
                      <div className="h-full rounded-full bg-stone-500" style={{ width: '96%' }} />
                    </div>
                  </div>
                  <ChevronRight
                    className="mt-1 h-4 w-4 shrink-0 text-stone-300"
                    strokeWidth={1.5}
                  />
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
    <div className="space-y-3 rounded-lg bg-stone-50 p-3 text-xs">
      {/* User message */}
      <div className="flex justify-end">
        <div className="max-w-[85%]">
          <div className="mb-1 flex items-center justify-end gap-1.5">
            <span className="text-[10px] font-medium text-stone-400">You</span>
            <div className="flex h-4 w-4 items-center justify-center rounded bg-stone-200">
              <User className="h-2.5 w-2.5 text-stone-500" strokeWidth={1.5} />
            </div>
          </div>
          <div className="pr-5 text-right text-stone-700">How does RLHF improve alignment?</div>
        </div>
      </div>
      {/* Agent message */}
      <div>
        <div className="mb-1 flex items-center gap-1.5">
          <div className="flex h-4 w-4 items-center justify-center rounded bg-stone-100">
            <img src={logoIcon} alt="" className="h-2.5 w-2.5" aria-hidden="true" />
          </div>
          <span className="text-[10px] font-medium text-stone-400">Arxivian</span>
        </div>
        <div className="pl-5 leading-relaxed text-stone-600">
          <strong className="text-stone-800">RLHF</strong> fine-tunes language models using human
          preference rankings to better align outputs with user intent.
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
          className="absolute right-0 left-0 flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2"
          style={{ opacity: paper.opacity, top: paper.offset }}
        >
          <FileText className="h-3.5 w-3.5 shrink-0 text-stone-400" strokeWidth={1.5} />
          <span className="font-mono text-[10px] text-stone-400">{paper.id}</span>
          <span className="truncate text-xs text-stone-600">{paper.title}</span>
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
        <Search className="h-3 w-3" strokeWidth={1.5} />
        <span>vector + full-text retrieval</span>
      </div>
      {/* Retrieved chunks */}
      <div className="space-y-1.5 text-[11px] leading-relaxed text-stone-500">
        <div className="flex items-center gap-2 rounded border border-stone-100 bg-white px-2.5 py-1.5">
          <span className="shrink-0 text-[10px] font-medium text-amber-700">0.94</span>
          <span className="truncate">
            ...self-attention mechanism allows the model to attend...
          </span>
        </div>
        <div className="flex items-center gap-2 rounded border border-stone-100 bg-white px-2.5 py-1.5">
          <span className="shrink-0 text-[10px] font-medium text-amber-700">0.87</span>
          <span className="truncate">
            ...multi-head attention projects queries, keys, and values...
          </span>
        </div>
      </div>
    </div>
  )
}

function CitationExplorerIllustration() {
  return (
    <div className="overflow-hidden rounded-lg border border-stone-200 bg-stone-50/80">
      {/* Root paper header */}
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-amber-50">
          <GitBranch className="h-3 w-3 text-amber-600" strokeWidth={1.5} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-0.5 flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-stone-400">1706.03762</span>
            <span className="text-[10px] text-stone-400">3 references</span>
          </div>
          <p className="truncate text-[11px] leading-snug text-stone-700">
            Attention Is All You Need
          </p>
        </div>
        <ChevronDown className="h-3 w-3 shrink-0 text-stone-300" strokeWidth={1.5} />
      </div>
      {/* Citation branches */}
      <div className="px-3 pb-2.5">
        <div className="ml-8 space-y-1 border-l-2 border-stone-200 pl-2.5">
          {[
            { num: 1, title: 'Neural Machine Translation by Jointly...', year: '2014' },
            { num: 2, title: 'Sequence to Sequence Learning with...', year: '2014' },
            { num: 3, title: 'Effective Approaches to Attention-based...', year: '2015' },
          ].map((ref) => (
            <div key={ref.num} className="flex items-center gap-1.5 text-[11px] text-stone-500">
              <span className="font-mono text-[10px] text-stone-400">{ref.num}.</span>
              <span className="truncate">{ref.title}</span>
              <span className="shrink-0 font-mono text-[10px] text-stone-300">{ref.year}</span>
            </div>
          ))}
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
    case 'Citation Explorer':
      return <CitationExplorerIllustration />
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
    icon: GitBranch,
    title: 'Citation Explorer',
    description:
      'Trace the lineage of ideas by exploring citation graphs -- see what a paper builds on and what builds on it.',
    size: 'small' as const,
  },
]

export default function LandingPage() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()
  const shouldReduceMotion = useReducedMotion()

  useEffect(() => {
    if (isSignedIn) {
      void navigate('/feed', { replace: true })
    }
  }, [isSignedIn, navigate])

  return (
    <div className="paper-grain flex min-h-screen flex-col bg-[#FAFAF9]">
      <PublicHeader />

      {/* Hero */}
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
              Understand research
              <br />
              at depth
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
              An intelligent research assistant that reads, indexes, and reasons over academic
              papers -- so you can focus on the ideas that matter.
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
                  {isSignedIn ? 'Open Chat' : 'Try a research question'}
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
      <section className="dot-grid relative z-10 px-4 pt-16 pb-24 sm:px-6 sm:pt-20 sm:pb-32 lg:px-8">
        <motion.div
          className="mx-auto max-w-6xl"
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-80px' }}
        >
          <motion.h2
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display mb-12 text-center text-2xl tracking-tight text-stone-900 sm:text-3xl"
          >
            Built for serious research
          </motion.h2>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, description, size }) => (
              <motion.div
                key={title}
                variants={shouldReduceMotion ? undefined : staggerItem}
                transition={transitions.base}
                whileHover={
                  shouldReduceMotion ? undefined : { y: -4, transition: { duration: 0.2 } }
                }
                className={clsx(
                  'flex flex-col rounded-xl border border-stone-200 bg-white p-6 transition-colors duration-200 hover:border-stone-300',
                  size === 'large' && 'md:col-span-2 lg:col-span-2'
                )}
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-stone-100">
                  <Icon className="h-5 w-5 text-stone-700" strokeWidth={1.5} />
                </div>
                <h3 className="font-display mb-2 text-lg font-semibold text-stone-900">{title}</h3>
                <p className="mb-4 text-sm leading-relaxed text-stone-500">{description}</p>
                <div className="mt-auto">
                  <FeatureIllustration title={title} />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Credibility */}
      <section
        id="credibility"
        className="relative z-10 bg-[#FAFAF9] px-4 pb-24 sm:px-6 sm:pb-32 lg:px-8"
      >
        {/* Top divider */}
        <div className="academic-divider mb-16" aria-hidden="true">
          <div className="academic-divider-line" />
          <div className="academic-divider-diamond" />
        </div>

        <motion.div
          className="mx-auto max-w-4xl text-center"
          variants={staggerContainer}
          initial="initial"
          whileInView="animate"
          viewport={{ once: true, margin: '-80px' }}
        >
          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="font-display mb-2 text-2xl tracking-tight text-stone-900 sm:text-3xl"
          >
            Search and ingest from arXiv's <span className="text-stone-500">2,400,000+</span> paper
            catalog
          </motion.p>

          <motion.p
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="mb-12 text-sm text-stone-400"
          >
            See it in action
          </motion.p>

          {/* Sample Q&A card */}
          <motion.div
            variants={shouldReduceMotion ? undefined : staggerItem}
            transition={transitions.base}
            className="mx-auto max-w-2xl rounded-xl border border-stone-200 bg-white text-left shadow-sm"
          >
            {/* Question */}
            <div className="p-5">
              <div className="flex justify-end">
                <div className="max-w-[80%]">
                  <div className="mb-2 flex items-center justify-end gap-2.5">
                    <span className="text-sm font-medium text-stone-500">You</span>
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                      <User className="h-3.5 w-3.5 text-stone-500" strokeWidth={1.5} />
                    </div>
                  </div>
                  <div className="pr-9 text-right text-sm leading-relaxed text-stone-800">
                    Summarize the key findings of arXiv:2301.07041
                  </div>
                </div>
              </div>
            </div>

            <hr className="border-stone-100" />

            {/* Answer */}
            <div className="p-5">
              <div className="mb-2 flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
                  <img src={logoIcon} alt="" className="h-4 w-4" aria-hidden="true" />
                </div>
                <span className="text-sm font-medium text-stone-500">Arxivian</span>
              </div>
              <div className="space-y-2 pl-9 text-sm leading-relaxed text-stone-600">
                <p>
                  The paper introduces{' '}
                  <strong className="text-stone-800">Retrieval-Augmented Generation (RAG)</strong>{' '}
                  as a framework for grounding language model outputs in retrieved evidence,
                  reducing hallucination and improving factual accuracy across knowledge-intensive
                  tasks.
                </p>
                <p>
                  Key findings include a 15% improvement in factual consistency over baseline
                  models, with the retrieval component enabling verifiable citations back to source
                  documents.
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

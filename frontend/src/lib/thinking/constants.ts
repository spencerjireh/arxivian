import type { LucideIcon } from 'lucide-react'
import {
  BookOpen, Search, FolderInput, List, GitBranch, BookMarked,
  PenLine, RotateCcw, Shield, Route, Zap, Award, Ban, CircleCheck, Download,
} from 'lucide-react'
import type { Variants } from 'framer-motion'
import type { ActivityStepKind, InternalStepKind } from '../../types/api'
import {
  rockVariants, bounceVariants, nudgeVariants, spinVariants,
  scalePulseVariants, pulseVariants,
} from '../animations'

export const STEP_ICONS: Record<ActivityStepKind | InternalStepKind, LucideIcon> = {
  retrieve: BookOpen,
  arxiv_search: Search,
  ingest: FolderInput,
  list_papers: List,
  explore_citations: GitBranch,
  propose_ingest: BookMarked,
  generating: PenLine,
  refining: RotateCcw,
  guardrail: Shield,
  routing: Route,
  executing: Zap,
  grading: Award,
  generation: PenLine,
  out_of_scope: Ban,
  confirming: CircleCheck,
  ingesting: Download,
}

export const STEP_ICON_COLORS: Record<ActivityStepKind | InternalStepKind, string> = {
  retrieve: 'text-amber-700',
  arxiv_search: 'text-amber-600',
  ingest: 'text-green-700',
  list_papers: 'text-stone-500',
  explore_citations: 'text-amber-700',
  propose_ingest: 'text-green-600',
  generating: 'text-stone-500',
  refining: 'text-amber-600',
  guardrail: 'text-stone-400',
  routing: 'text-stone-400',
  executing: 'text-stone-400',
  grading: 'text-stone-400',
  generation: 'text-stone-400',
  out_of_scope: 'text-stone-400',
  confirming: 'text-amber-600',
  ingesting: 'text-green-600',
}

export const STEP_ANIMATION_VARIANTS: Record<ActivityStepKind | InternalStepKind, Variants> = {
  // Search/Scan -- gentle rock
  retrieve: rockVariants,
  arxiv_search: rockVariants,
  explore_citations: rockVariants,
  // Data I/O -- soft bounce
  ingest: bounceVariants,
  ingesting: bounceVariants,
  propose_ingest: bounceVariants,
  // Writing -- micro-nudge X
  generating: nudgeVariants,
  generation: nudgeVariants,
  // Writing -- continuous spin
  refining: spinVariants,
  // Evaluation -- scale pulse
  list_papers: scalePulseVariants,
  grading: scalePulseVariants,
  // Control flow -- opacity pulse
  guardrail: pulseVariants,
  routing: pulseVariants,
  executing: pulseVariants,
  out_of_scope: pulseVariants,
  confirming: pulseVariants,
}

export const TOOL_LABELS: Record<string, { label: string; pastVerb: string }> = {
  retrieve_chunks: { label: 'Retrieving relevant sections', pastVerb: 'Retrieved' },
  arxiv_search: { label: 'Searching arXiv', pastVerb: 'Searched arXiv' },
  ingest_papers: { label: 'Adding papers to library', pastVerb: 'Added' },
  list_papers: { label: 'Listing papers', pastVerb: 'Listed papers' },
  explore_citations: { label: 'Exploring citations', pastVerb: 'Explored citations' },
  propose_ingest: { label: 'Proposing papers to add', pastVerb: 'Proposed' },
}

export const TOOL_TO_KIND: Record<string, ActivityStepKind> = {
  retrieve_chunks: 'retrieve',
  arxiv_search: 'arxiv_search',
  ingest_papers: 'ingest',
  list_papers: 'list_papers',
  explore_citations: 'explore_citations',
  propose_ingest: 'propose_ingest',
}

export const INTERNAL_LABELS: Record<InternalStepKind, string> = {
  guardrail: 'Guardrail',
  routing: 'Routing',
  executing: 'Executing',
  grading: 'Grading',
  generation: 'Generating',
  out_of_scope: 'Out of Scope',
  confirming: 'Confirming',
  ingesting: 'Ingesting',
}

const INTERNAL_STEP_LIST = [
  'guardrail', 'routing', 'executing', 'grading',
  'generation', 'out_of_scope', 'confirming', 'ingesting',
] as const satisfies readonly InternalStepKind[]

export const INTERNAL_STEP_NAMES: Set<string> = new Set(INTERNAL_STEP_LIST)

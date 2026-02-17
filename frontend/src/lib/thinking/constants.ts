import type { LucideIcon } from 'lucide-react'
import {
  BookOpen, Search, FolderInput, FileText, List, GitBranch, BookMarked,
  PenLine, RotateCcw, Shield, Route, Zap, Award, Ban, CircleCheck, Download,
} from 'lucide-react'
import type { ActivityStepKind, InternalStepKind } from '../../types/api'

export const STEP_ICONS: Record<ActivityStepKind | InternalStepKind, LucideIcon> = {
  retrieve: BookOpen,
  arxiv_search: Search,
  ingest: FolderInput,
  summarize_paper: FileText,
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
  summarize_paper: 'text-stone-600',
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
  confirming: 'text-stone-400',
  ingesting: 'text-stone-400',
}

export const TOOL_LABELS: Record<string, { label: string; pastVerb: string }> = {
  retrieve_chunks: { label: 'Retrieving relevant sections', pastVerb: 'Retrieved' },
  arxiv_search: { label: 'Searching arXiv', pastVerb: 'Searched arXiv' },
  ingest_papers: { label: 'Adding papers to library', pastVerb: 'Added' },
  summarize_paper: { label: 'Summarizing paper', pastVerb: 'Summarized' },
  list_papers: { label: 'Listing papers', pastVerb: 'Listed papers' },
  explore_citations: { label: 'Exploring citations', pastVerb: 'Explored citations' },
  propose_ingest: { label: 'Proposing papers to add', pastVerb: 'Proposed' },
}

export const TOOL_TO_KIND: Record<string, ActivityStepKind> = {
  retrieve_chunks: 'retrieve',
  arxiv_search: 'arxiv_search',
  ingest_papers: 'ingest',
  summarize_paper: 'summarize_paper',
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

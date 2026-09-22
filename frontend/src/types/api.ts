// API types mirroring backend schemas

// Stream types (paper-scoped chat)

export interface StreamRequest {
  query: string
  /** The ingested paper this conversation is scoped to. */
  arxiv_id: string
  session_id?: string
}

export type StreamEventType =
  'status' | 'content' | 'sources' | 'metadata' | 'error' | 'done' | 'citations'

export interface StatusEventData {
  step: string
  message: string
  details?: Record<string, unknown>
}

export interface ContentEventData {
  token: string
}

export interface SourceInfo {
  arxiv_id: string
  title: string
  authors: string[]
  pdf_url: string
  relevance_score: number
  published_date?: string
  was_graded_relevant?: boolean
}

export interface SourcesEventData {
  sources: SourceInfo[]
}

export interface MetadataEventData {
  query: string
  execution_time_ms: number
  retrieval_attempts: number
  guardrail_score?: number
  session_id?: string
  turn_number: number
}

export interface ErrorEventData {
  error: string
  code?: string
}

export interface MessageError {
  message: string
  code: string
}

// Citation explorer types

export interface CitationsEventData {
  arxiv_id: string
  title: string
  reference_count: number
  references: string[]
}

// Conversation types

export interface ConversationTurn {
  turn_number: number
  user_query: string
  agent_response: string
  provider: string
  model: string
  guardrail_score?: number | null
  retrieval_attempts: number
  rewritten_query?: string | null
  sources?: Record<string, unknown>[] | null
  reasoning_steps?: string[] | null
  citations?: Record<string, unknown> | null
  created_at: string
}

interface ConversationListItem {
  session_id: string
  arxiv_id?: string | null
  title?: string
  turn_count: number
  created_at: string
  updated_at: string
  last_query?: string
}

export interface ConversationListResponse {
  total: number
  offset: number
  limit: number
  conversations: ConversationListItem[]
}

export interface ConversationDetailResponse {
  session_id: string
  arxiv_id?: string | null
  title?: string
  created_at: string
  updated_at: string
  turns: ConversationTurn[]
}

// User/Tier types

export interface MeResponse {
  id: string
  email: string | null
  first_name: string | null
  last_name: string | null
  tier: 'free' | 'pro'
  daily_chat_limit: number | null // null = unlimited
  chats_used_today: number
  preferences?: UserPreferences
  onboarded?: boolean
}

export interface FeedProfileInput {
  categories: string[]
  compute_profile: ComputeProfile
  keywords: string[]
}

export type ComputeProfile = 'laptop' | 'single_gpu' | 'cloud'

interface FeedProfile {
  categories: string[]
  compute_profile: ComputeProfile | null
  keywords: string[]
}

interface UserPreferences {
  feed_profile?: FeedProfile
}

// Chat UI types

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  metadata?: MetadataEventData
  isStreaming?: boolean
  error?: MessageError
  createdAt: Date
  citations?: CitationsEventData
}

// Feed / scoring types (Phase 2, SPE-274)

export type PaperLifecycleState = 'saved' | 'dismissed' | 'implementing' | 'shipped'

export interface PaperState {
  state: PaperLifecycleState
  repo_url: string | null
  dismissal_reason: string | null
  updated_at: string
}

export interface SetPaperStateBody {
  state: PaperLifecycleState
  repo_url?: string
  dismissal_reason?: string
}

export interface FeedPaper {
  arxiv_id: string
  title: string
  authors: string[]
  categories: string[]
  published_date: string
  pdf_url: string
}

export type ScoreDimension =
  'method_clarity' | 'resource_feasibility' | 'data_availability' | 'demand'

interface FeedScores {
  method_clarity: number | null
  resource_feasibility: number | null
  data_availability: number | null
  demand: number | null
  composite: number
}

/** The four derived sub-scores a card meter draws; null is "not available", never low. */
export type DimensionScores = Pick<FeedScores, ScoreDimension>

/** One card. The library can carry a paper without a current score, so the score-derived
 *  fields are nullable; the feed always fills them. */
export interface FeedItem {
  paper: FeedPaper
  scores: FeedScores | null
  /** "<Model family> for <task type>" built from the stored attributes. */
  headline: string | null
  /** Ordered truthy-only phrases (compute tier, data access, code, weights, pseudocode, hyperparameters). */
  meta: string[]
  /** null without a compute profile (or when anonymous). */
  compute_match: boolean | null
  low_confidence: ScoreDimension[]
  keyword_match: boolean
  state: PaperState | null
  scored_at: string | null
}

/** GET /users/me/library: the caller's papers grouped by lifecycle state (SPE-296). */
export type LibraryGroup = Exclude<PaperLifecycleState, 'dismissed'>

export type LibraryResponse = Record<LibraryGroup, FeedItem[]>

export interface AvailableWeek {
  week_start: string
  paper_count: number
}

export interface FeedResponse {
  week_start: string | null
  available_weeks: AvailableWeek[]
  categories_available: string[]
  total: number
  offset: number
  limit: number
  items: FeedItem[]
}

export interface FeedParams {
  week?: string
  category?: string
  min_score?: number
  include_dismissed?: boolean
  limit?: number
}

// Paper score detail (Phase 2, SPE-276)

export type ScoreBand = 'LOW' | 'MED' | 'HIGH'
type JudgmentKind = 'noul' | 'choice' | 'score'
type EvidenceKind = 'pseudocode' | 'compute' | 'dataset' | 'citation' | 'code'

export interface Judgment {
  key: string
  kind: JudgmentKind
  answer: string | number | boolean
  probabilities: Record<string, number>
  confidence: number
  legend: string[] | null
}

export interface EvidenceSpan {
  // The backend may add kinds before the client learns them; keep the union open.
  kind: EvidenceKind | (string & {})
  text: string
  source: string | null
}

export interface DimensionDetail {
  dimension: ScoreDimension
  band: ScoreBand
  score: number
  level: number
  max_level: number
  expected: number
  probabilities: Record<string, number>
  confidence: number
  judgments: Judgment[]
  evidence: EvidenceSpan[]
  reasoning: string
}

export interface PaperAttributes {
  code_released: Judgment | null
  task_type: Judgment | null
  model_family: Judgment | null
  code_evidence: EvidenceSpan[]
}

/** FeedPaper plus the abstract: the detail header and the 202 body. */
export interface PaperMetadata extends FeedPaper {
  abstract: string
}

export interface PaperScoreDetail {
  paper: PaperMetadata
  rubric_version: string
  scored_at: string
  scores: FeedScores
  headline: string
  meta: string[]
  compute_match: boolean | null
  low_confidence: ScoreDimension[]
  state: PaperState | null
  attributes: PaperAttributes
  dimensions: DimensionDetail[]
}

export interface PaperScorePending {
  status: 'pending'
  arxiv_id: string
  paper: PaperMetadata
  /** null for an anonymous reader: nothing was enqueued. */
  task_id: string | null
}

export type PaperScoreResult =
  | { status: 'ready'; detail: PaperScoreDetail }
  | { status: 'pending'; task_id: string | null; paper: PaperMetadata }

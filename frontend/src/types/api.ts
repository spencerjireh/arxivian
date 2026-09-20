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

// Paper types

export interface PaperListItem {
  arxiv_id: string
  title: string
  authors: string[]
  abstract: string
  categories: string[]
  published_date: string
  pdf_url: string
  sections: string[] | null
  pdf_processed: boolean
  pdf_processing_date: string | null
  parser_used: string | null
  created_at: string
  updated_at: string
}

export interface PaperListResponse {
  total: number
  offset: number
  limit: number
  papers: PaperListItem[]
}

export interface PaperListParams {
  offset?: number
  limit?: number
  processed_only?: boolean
  category?: string
  author?: string
  sort_by?: 'created_at' | 'published_date' | 'updated_at'
  sort_order?: 'asc' | 'desc'
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

interface FeedScores {
  method_clarity: number | null
  resource_feasibility: number | null
  data_availability: number | null
  demand: number | null
  composite: number
}

export interface FeedSignals {
  pseudocode_present: boolean
  public_datasets: boolean
  single_gpu: boolean
  code_released: boolean
  compute_match: boolean | null
}

export type ScoreDimension =
  'method_clarity' | 'resource_feasibility' | 'data_availability' | 'demand'

export interface FeedItem {
  paper: FeedPaper
  scores: FeedScores
  verdict: string
  signals: FeedSignals
  low_confidence: ScoreDimension[]
  keyword_match: boolean
  state: PaperState | null
  scored_at: string
}

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

export interface PaperScoreDetail {
  paper: FeedPaper
  rubric_version: string
  scored_at: string
  scores: FeedScores
  verdict: string
  signals: FeedSignals
  low_confidence: ScoreDimension[]
  state: PaperState | null
  attributes: PaperAttributes
  dimensions: DimensionDetail[]
}

export interface PaperScorePending {
  status: 'pending'
  arxiv_id: string
  task_id: string | null
}

export type PaperScoreResult =
  { status: 'ready'; detail: PaperScoreDetail } | { status: 'pending'; task_id: string | null }

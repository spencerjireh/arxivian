// API types mirroring backend schemas

// Stream types

export type LLMProvider = 'openai' | 'nvidia_nim'

export interface StreamRequest {
  query: string
  provider?: LLMProvider
  model?: string
  top_k?: number
  guardrail_threshold?: number
  max_retrieval_attempts?: number
  temperature?: number
  session_id?: string
  conversation_window?: number
}

export type StreamEventType = 'status' | 'content' | 'sources' | 'metadata' | 'error' | 'done'

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
  rewritten_query?: string
  guardrail_score?: number
  provider: string
  model: string
  session_id?: string
  turn_number: number
  reasoning_steps: string[]
}

export interface ErrorEventData {
  error: string
  code?: string
}

// Persisted thinking step shape (from backend JSONB)

export interface PersistedThinkingStep {
  step: string
  message: string
  details?: Record<string, unknown> | null
  tool_name?: string | null
  started_at: string
  completed_at: string
}

// Thinking/Reasoning types for UI

export type ActivityStepKind =
  | 'retrieve'
  | 'arxiv_search'
  | 'ingest'
  | 'summarize_paper'
  | 'list_papers'
  | 'explore_citations'
  | 'propose_ingest'
  | 'generating'
  | 'refining'

export type InternalStepKind =
  | 'guardrail'
  | 'routing'
  | 'executing'
  | 'grading'
  | 'generation'
  | 'out_of_scope'
  | 'confirming'
  | 'ingesting'

export type ThinkingStepStatus = 'running' | 'complete' | 'error'

export interface ActivityStep {
  id: string
  kind: ActivityStepKind
  toolName: string
  label: string
  message: string
  details?: Record<string, unknown>
  status: ThinkingStepStatus
  startTime: Date
  endTime?: Date
  isInternal: false
}

export interface InternalStep {
  id: string
  kind: InternalStepKind
  label: string
  message: string
  details?: Record<string, unknown>
  status: ThinkingStepStatus
  startTime: Date
  endTime?: Date
  isInternal: true
}

export type ThinkingStep = ActivityStep | InternalStep

// Conversation types

export interface ConversationTurnResponse {
  turn_number: number
  user_query: string
  agent_response: string
  provider: string
  model: string
  guardrail_score?: number
  retrieval_attempts: number
  rewritten_query?: string
  sources?: Record<string, unknown>[]
  reasoning_steps?: string[]
  thinking_steps?: PersistedThinkingStep[] | null
  created_at: string
}

export interface ConversationListItem {
  session_id: string
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
  created_at: string
  updated_at: string
  turns: ConversationTurnResponse[]
}

export interface DeleteConversationResponse {
  session_id: string
  turns_deleted: number
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
  daily_chat_limit: number | null  // null = unlimited
  chats_used_today: number
  can_select_model: boolean
}

// Chat UI types

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceInfo[]
  metadata?: MetadataEventData
  thinkingSteps?: ThinkingStep[]
  isStreaming?: boolean
  error?: string
  createdAt: Date
}

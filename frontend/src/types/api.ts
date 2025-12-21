// API types mirroring backend schemas

// Stream types

export type LLMProvider = 'openai' | 'zai'

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

export const StreamEventType = {
  STATUS: 'status',
  CONTENT: 'content',
  SOURCES: 'sources',
  METADATA: 'metadata',
  ERROR: 'error',
  DONE: 'done',
} as const

export type StreamEventType = (typeof StreamEventType)[keyof typeof StreamEventType]

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

// Thinking/Reasoning types for UI

export type ThinkingStepType =
  | 'guardrail'
  | 'routing'
  | 'executing'
  | 'grading'
  | 'generation'
  | 'out_of_scope'

export type ThinkingStepStatus = 'running' | 'complete' | 'error'

export interface ThinkingStep {
  id: string
  step: ThinkingStepType
  message: string
  details?: Record<string, unknown>
  status: ThinkingStepStatus
  timestamp: Date
  startTime: Date
  endTime?: Date
  order: number
}

// Step order mapping for workflow visualization
export const STEP_ORDER: Record<ThinkingStepType, number> = {
  guardrail: 1,
  routing: 2,
  executing: 3,
  grading: 4,
  generation: 5,
  out_of_scope: 5, // Same as generation (alternative path)
}

// Step display labels
export const STEP_LABELS: Record<ThinkingStepType, string> = {
  guardrail: 'Guardrail',
  routing: 'Routing',
  executing: 'Retrieval',
  grading: 'Grading',
  generation: 'Generating',
  out_of_scope: 'Out of Scope',
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
  createdAt: Date
}

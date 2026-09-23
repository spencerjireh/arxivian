// API types: named aliases over the generated OpenAPI schemas (api.gen.ts, refreshed by
// `just types`) plus the client-only shapes (chat messages, the score result union, feed
// query params). Add an alias here when a module needs a backend schema; never edit api.gen.ts.
import type { components } from './api.gen'

type Schemas = components['schemas']

// Stream (paper-scoped chat; backend schemas/stream.py)

export type StreamRequest = Schemas['StreamRequest']
export type StreamEventType = Schemas['StreamEventType']
export type StatusEventData = Schemas['StatusEventData']
export type ContentEventData = Schemas['ContentEventData']
export type SourceInfo = Schemas['SourceInfo']
export type SourcesEventData = Schemas['SourcesEventData']
export type MetadataEventData = Schemas['MetadataEventData']
export type ErrorEventData = Schemas['ErrorEventData']
export type CitationsEventData = Schemas['CitationsEventData']

/** The error envelope every route can answer with (backend schemas/errors.py). */
export type ApiErrorResponse = Schemas['ErrorResponse']

// Conversations (backend schemas/conversations.py)

export type ConversationTurn = Schemas['ConversationTurnResponse']
export type ConversationListResponse = Schemas['ConversationListResponse']
export type ConversationDetailResponse = Schemas['ConversationDetailResponse']

// Users (backend schemas/users.py)

export type MeResponse = Schemas['MeResponse']
export type FeedProfileInput = Schemas['UpdatePreferencesRequest']
export type ComputeProfile = NonNullable<Schemas['FeedProfile']['compute_profile']>

// Chat UI (client only)

export interface MessageError {
  message: string
  code: string
}

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

// Feed and lifecycle (backend schemas/feed.py, paper_states.py)

export type PaperState = Schemas['UserPaperStateResponse']
export type PaperLifecycleState = PaperState['state']
export type SetPaperStateBody = Schemas['UserPaperStateRequest']
export type FeedPaper = Schemas['FeedPaper']
export type ScoreDimension = Schemas['DimensionDetail']['dimension']
type FeedScores = Schemas['FeedScores']

/** The four derived sub-scores a card meter draws; null is "not available", never low. */
export type DimensionScores = Pick<FeedScores, ScoreDimension>

export type FeedItem = Schemas['FeedItem']
export type LibraryResponse = Schemas['LibraryResponse']
export type LibraryGroup = keyof LibraryResponse
export type AvailableWeek = Schemas['AvailableWeek']
export type FeedResponse = Schemas['FeedResponse']

/** GET /feed query parameters as the client builds them (client only). */
export interface FeedParams {
  week?: string
  category?: string
  min_score?: number
  include_dismissed?: boolean
  limit?: number
}

// Paper score detail (backend schemas/papers.py)

export type ScoreBand = Schemas['DimensionDetail']['band']
export type Judgment = Schemas['Judgment']
export type EvidenceSpan = Schemas['EvidenceItem']
export type DimensionDetail = Schemas['DimensionDetail']
export type PaperAttributes = Schemas['PaperAttributesDetail']
export type PaperMetadata = Schemas['PaperMetadata']
export type PaperScoreDetail = Schemas['PaperScoreDetailResponse']
export type PaperScorePending = Schemas['ScorePendingResponse']

/** GET /papers/{id}/score as the client keeps it: the 200 body or the 202 (client only). */
export type PaperScoreResult =
  | { status: 'ready'; detail: PaperScoreDetail }
  | { status: 'pending'; task_id: string | null; paper: PaperMetadata }

# Chat Implementation Plan

Frontend implementation for `/stream` SSE endpoint and conversation management APIs.

## Dependencies

```bash
npm install zustand @tanstack/react-query @microsoft/fetch-event-source
```

## File Structure

```
src/
  api/
    client.ts              # Base fetch wrapper
    conversations.ts       # Conversation REST + TanStack Query hooks
    stream.ts              # SSE stream handler (POST with fetch-event-source)
  stores/
    chatStore.ts           # Zustand chat state
  types/
    api.ts                 # Backend schema mirrors
  components/
    chat/
      ChatMessage.tsx      # User/assistant message bubble
      ChatMessages.tsx     # Message list container
      ChatInput.tsx        # Input + expandable advanced options
      StreamStatus.tsx     # Workflow step indicator
      SourceCard.tsx       # Expandable source citation
      MetadataPanel.tsx    # Expandable execution metadata
    conversations/
      ConversationList.tsx # Past conversations list
      ConversationItem.tsx # Single list item
  pages/
    AskPage.tsx            # /ask - conversation list + new chat button
    ChatPage.tsx           # /ask/:sessionId or /ask/new - active chat
  hooks/
    useStreamChat.ts       # SSE + store orchestration
```

## Routes

| Path | Component | Description |
|------|-----------|-------------|
| `/ask` | AskPage | Conversation list, "New Chat" button |
| `/ask/new` | ChatPage | Fresh chat, sessionId assigned on first response |
| `/ask/:sessionId` | ChatPage | Existing conversation, fetches history on mount |

## Types (api.ts)

Mirror backend schemas:
- `StreamRequest`, `StreamEventType`
- `StatusEventData`, `ContentEventData`, `SourcesEventData`, `MetadataEventData`, `ErrorEventData`
- `ConversationListItem`, `ConversationListResponse`, `ConversationDetailResponse`, `ConversationTurnResponse`
- `SourceInfo`

## Zustand Store (chatStore.ts)

```ts
interface ChatState {
  sessionId: string | null
  messages: Message[]
  isStreaming: boolean
  currentStatus: string | null
  streamingContent: string
  sources: SourceInfo[]
  error: string | null
  
  // Actions
  setSessionId(id: string): void
  addUserMessage(content: string): void
  appendToken(token: string): void
  setStatus(status: string | null): void
  setSources(sources: SourceInfo[]): void
  finalizeMessage(metadata: MetadataEventData): void
  setError(error: string): void
  loadHistory(turns: ConversationTurnResponse[]): void
  reset(): void
}
```

## API Layer

### client.ts
- `apiGet<T>(path)`, `apiPost<T>(path, body)`, `apiDelete(path)`
- Base URL: `/api`

### conversations.ts (TanStack Query)
- `useConversations(offset, limit)` - paginated list
- `useConversation(sessionId)` - single conversation with turns
- `useDeleteConversation()` - mutation

### stream.ts
- `streamChat(request, callbacks)` - Uses `fetchEventSource`
- Callbacks: `onStatus`, `onContent`, `onSources`, `onMetadata`, `onError`, `onDone`

## Hook: useStreamChat

Orchestrates store + stream:
1. Add user message to store
2. Set streaming state
3. Call `streamChat` with callbacks wired to store actions
4. On metadata event: capture sessionId, finalize message
5. On done: clear streaming state

## Components

### ChatMessage
- User: right-aligned, `bg-gray-100`
- Assistant: left-aligned, `bg-white border`
- Streaming: trailing cursor animation

### ChatInput
- Text input + Send button
- Expandable "Advanced" section:
  - Provider (openai/zai)
  - Model (text input)
  - Temperature (slider 0-1)
  - Top K (1-10)
  - Guardrail threshold (0-100)

### StreamStatus
- Small pill above input: "Checking guardrail...", "Retrieving...", "Generating..."
- Fade in/out transitions

### SourceCard
- Collapsed: arxiv_id + title (truncated)
- Expanded: authors, pdf_url, relevance_score

### MetadataPanel
- Collapsed: "View details"
- Expanded: execution_time, retrieval_attempts, provider, model, reasoning_steps

### ConversationList
- List items: session_id (truncated), turn_count, last_query preview, relative time
- Delete button per item

## Pages

### AskPage
- "New Chat" button -> navigate to `/ask/new`
- ConversationList with click -> navigate to `/ask/:sessionId`

### ChatPage
- If `sessionId !== 'new'`: fetch conversation history on mount, load into store
- ChatMessages + ChatInput
- On first response metadata: update URL from `/ask/new` to `/ask/:actualSessionId` (useNavigate replace)

## Design

Minimal zen:
- Gray/slate palette, monochrome
- Generous whitespace
- Subtle borders (`border-gray-200`)
- Small text for metadata
- Smooth transitions (`transition-all duration-200`)

## Implementation Order

1. Install dependencies
2. `types/api.ts`
3. `api/client.ts`
4. `api/conversations.ts`
5. `api/stream.ts`
6. `stores/chatStore.ts`
7. `hooks/useStreamChat.ts`
8. Components: ChatMessage, ChatInput, StreamStatus
9. Components: SourceCard, MetadataPanel
10. Components: ConversationList, ConversationItem
11. Pages: AskPage, ChatPage
12. Update App.tsx routes + TanStack QueryProvider
13. Polish styling

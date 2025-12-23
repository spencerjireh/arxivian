import { useRef, useEffect } from 'react'
import type { Message } from '../types/api'

export interface AutoScrollOptions {
  behavior?: ScrollBehavior
  enabled?: boolean
}

export function useAutoScroll(messages: Message[], options: AutoScrollOptions = {}) {
  const { behavior = 'smooth', enabled = true } = options
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevMessagesLengthRef = useRef(messages.length)
  const prevLastMessageContentRef = useRef('')

  useEffect(() => {
    if (!enabled) return

    const messagesAdded = messages.length > prevMessagesLengthRef.current
    const lastMessage = messages[messages.length - 1]
    const isStreaming = lastMessage?.isStreaming
    const contentChanged = lastMessage?.content !== prevLastMessageContentRef.current

    // Scroll on: new message, streaming message, or content change
    if (messagesAdded || isStreaming || (isStreaming && contentChanged)) {
      scrollRef.current?.scrollIntoView({ behavior })
    }

    prevMessagesLengthRef.current = messages.length
    prevLastMessageContentRef.current = lastMessage?.content || ''
  }, [messages.length, messages, behavior, enabled])

  return scrollRef
}

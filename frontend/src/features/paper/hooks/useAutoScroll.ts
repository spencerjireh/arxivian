// useAutoScroll: keeps a message list pinned to the bottom while new turns stream in.
import { useRef, useEffect } from 'react'
import type { Message } from '@/types/api'

interface AutoScrollOptions {
  behavior?: ScrollBehavior
  enabled?: boolean
}

export function useAutoScroll(messages: Message[], options: AutoScrollOptions = {}) {
  const { behavior = 'smooth', enabled = true } = options
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevMessagesLengthRef = useRef(messages.length)

  useEffect(() => {
    if (!enabled) return

    const messagesAdded = messages.length > prevMessagesLengthRef.current
    const lastMessage = messages[messages.length - 1]

    // Scroll on a new message and on every content change of a streaming one (the
    // `messages` dependency re-runs the effect per token).
    if (messagesAdded || lastMessage?.isStreaming) {
      scrollRef.current?.scrollIntoView({ behavior })
    }

    prevMessagesLengthRef.current = messages.length
  }, [messages, behavior, enabled])

  return scrollRef
}

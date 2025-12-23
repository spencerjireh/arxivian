import { motion, useReducedMotion } from 'framer-motion'
import { Loader2, Trash2 } from 'lucide-react'
import type { ConversationListItem } from '../../types/api'
import { transitions } from '../../lib/animations'

interface SidebarConversationItemProps {
  conversation: ConversationListItem
  isActive: boolean
  onClick: () => void
  onDelete: () => void
  isDeleting?: boolean
}

function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str
  return str.slice(0, maxLen - 1) + '\u2026'
}

export default function SidebarConversationItem({
  conversation,
  isActive,
  onClick,
  onDelete,
  isDeleting,
}: SidebarConversationItemProps) {
  const shouldReduceMotion = useReducedMotion()

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete()
  }

  return (
    <motion.div
      onClick={onClick}
      className={`
        group relative px-3 py-1.5 rounded-lg cursor-pointer
        transition-colors duration-150
        ${isActive
          ? 'bg-stone-100'
          : 'hover:bg-stone-100'
        }
      `}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className={`text-sm leading-tight truncate ${isActive ? 'text-stone-900 font-medium' : 'text-stone-700'}`}>
            {conversation.last_query
              ? truncate(conversation.last_query, 50)
              : 'New conversation'}
          </p>
        </div>

        <motion.button
          onClick={handleDelete}
          disabled={isDeleting}
          whileHover={shouldReduceMotion ? {} : { scale: 1.1 }}
          whileTap={shouldReduceMotion ? {} : { scale: 0.9 }}
          transition={transitions.fast}
          className="
            p-1.5 rounded-md opacity-0 group-hover:opacity-100
            text-stone-400 hover:text-red-600 hover:bg-red-50
            transition-all duration-150 disabled:opacity-50
            flex-shrink-0
          "
          aria-label="Delete conversation"
        >
          {isDeleting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" strokeWidth={1.5} />
          ) : (
            <Trash2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
        </motion.button>
      </div>
    </motion.div>
  )
}

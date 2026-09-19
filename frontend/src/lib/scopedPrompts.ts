import { AlertTriangle, BookOpen, FolderGit2 } from 'lucide-react'
import type { Suggestion } from '../components/chat/SuggestionChips'

/** Seeded prompts for the paper-scoped chat panel (feed-prd section 5). */
export const SCOPED_PROMPTS: Suggestion[] = [
  {
    icon: BookOpen,
    title: 'Explain the core method',
    prompt: 'Explain the core method of this paper.',
  },
  {
    icon: FolderGit2,
    title: 'What would a minimal repo look like',
    prompt:
      'What would a minimal repository implementing this paper look like? List the modules, the key functions, and the order to build them.',
  },
  {
    icon: AlertTriangle,
    title: 'What are the risky parts to reproduce',
    prompt: 'What are the riskiest parts of reproducing this paper, and how would I de-risk each one?',
  },
]

// Feed: dismissible prompt for a signed-in reader without a feed profile (replaces the onboarding gate).
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { SlidersHorizontal, X } from 'lucide-react'
import Button from '@/components/ui/Button'
import { useSession } from '@/lib/auth'

export const ONBOARDING_PROMPT_KEY = 'arxivian:onboarding-prompt-dismissed'

function readDismissed(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_PROMPT_KEY) === '1'
  } catch {
    return false
  }
}

/** `me` is only ever loaded for a signed-in reader, so `onboarded === false` is the whole gate. */
export default function OnboardingPrompt() {
  const onboarded = useSession().me?.onboarded
  const [dismissed, setDismissed] = useState(readDismissed)

  if (onboarded !== false || dismissed) return null

  const dismiss = () => {
    try {
      localStorage.setItem(ONBOARDING_PROMPT_KEY, '1')
    } catch {
      // Storage may be unavailable; the prompt still hides for this visit.
    }
    setDismissed(true)
  }

  return (
    <aside
      aria-label="Set up your feed"
      className="mb-6 flex flex-wrap items-center gap-3 rounded-xl border border-stone-200 bg-white px-5 py-4"
    >
      <SlidersHorizontal className="h-5 w-5 shrink-0 text-stone-400" strokeWidth={1.5} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-stone-900">Set your compute and categories</p>
        <p className="text-sm text-stone-500">
          About 30 seconds. Papers that fit your hardware move up, and your categories come first.
        </p>
      </div>
      <Link to="/onboarding">
        <Button variant="primary" size="sm">
          Set up
        </Button>
      </Link>
      <Button variant="icon" size="sm" onClick={dismiss} aria-label="Dismiss">
        <X className="h-4 w-4" strokeWidth={1.5} />
      </Button>
    </aside>
  )
}

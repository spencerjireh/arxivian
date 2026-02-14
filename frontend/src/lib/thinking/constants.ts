import type { LucideIcon } from 'lucide-react'
import { Shield, CircleSlash, GitFork, Zap, CheckCheck, Sparkles } from 'lucide-react'
import type { ThinkingStepType } from '../../types/api'

interface StepConfig {
  order: number
  label: string
  icon: LucideIcon
  /** Whether this step is shown by default (without "show internals" toggle) */
  visible: boolean
}

export const STEP_CONFIG: Record<ThinkingStepType, StepConfig> = {
  guardrail: { order: 0, label: 'Guardrail', icon: Shield, visible: false },
  out_of_scope: { order: 1, label: 'Out of Scope', icon: CircleSlash, visible: false },
  routing: { order: 2, label: 'Routing', icon: GitFork, visible: false },
  executing: { order: 3, label: 'Executing', icon: Zap, visible: true },
  grading: { order: 4, label: 'Grading', icon: CheckCheck, visible: false },
  generation: { order: 5, label: 'Generating', icon: Sparkles, visible: true },
}
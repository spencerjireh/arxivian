import type { ThinkingStepType } from '../../types/api'

interface StepConfig {
  order: number
  label: string
  /** Whether this step is shown by default (without "show internals" toggle) */
  visible: boolean
}

export const STEP_CONFIG: Record<ThinkingStepType, StepConfig> = {
  guardrail: { order: 0, label: 'Guardrail', visible: false },
  out_of_scope: { order: 1, label: 'Out of Scope', visible: false },
  routing: { order: 2, label: 'Routing', visible: false },
  executing: { order: 3, label: 'Executing', visible: true },
  grading: { order: 4, label: 'Grading', visible: false },
  generation: { order: 5, label: 'Generating', visible: true },
}

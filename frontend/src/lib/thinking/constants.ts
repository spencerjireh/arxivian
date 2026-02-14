import type { ThinkingStepType } from '../../types/api'

export const STEP_ORDER: Record<ThinkingStepType, number> = {
  guardrail: 0,
  out_of_scope: 1,
  routing: 2,
  executing: 3,
  grading: 4,
  generation: 5,
}

export const STEP_LABELS: Record<ThinkingStepType, string> = {
  guardrail: 'Guardrail',
  out_of_scope: 'Out of Scope',
  routing: 'Routing',
  executing: 'Executing',
  grading: 'Grading',
  generation: 'Generating',
}

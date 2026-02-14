import type { ThinkingStepType } from '../../types/api'

const STEP_TYPE_MAP: Record<string, ThinkingStepType> = {
  guardrail: 'guardrail',
  out_of_scope: 'out_of_scope',
  routing: 'routing',
  executing: 'executing',
  grading: 'grading',
  generation: 'generation',
}

export function mapStepType(step: string): ThinkingStepType {
  return STEP_TYPE_MAP[step] ?? 'executing'
}

export function isCompletionMessage(step: string, message: string): boolean {
  switch (step) {
    case 'guardrail':
      return message.startsWith('Query is')
    case 'out_of_scope':
      return message.startsWith('Generating out-of-scope')
    case 'routing':
      return message.startsWith('Decided to')
    case 'executing':
      return message.startsWith('Executed ') || message === 'Tool completed' || message === 'Tool failed'
    case 'grading':
      return message.startsWith('Found ')
    case 'generation':
      return message.startsWith('Generating answer')
    default:
      return false
  }
}

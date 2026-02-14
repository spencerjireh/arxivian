import type { ThinkingStepType } from '../../types/api'
import { STEP_CONFIG } from './constants'

const VALID_STEPS = new Set<string>(Object.keys(STEP_CONFIG))

export function mapStepType(step: string): ThinkingStepType {
  return VALID_STEPS.has(step) ? (step as ThinkingStepType) : 'executing'
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

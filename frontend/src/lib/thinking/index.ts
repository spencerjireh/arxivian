import type { ThinkingStepType } from '../../types/api'
import { STEP_CONFIG } from './constants'

const VALID_STEPS = new Set<string>(Object.keys(STEP_CONFIG))

export function mapStepType(step: string): ThinkingStepType {
  return VALID_STEPS.has(step) ? (step as ThinkingStepType) : 'executing'
}

/** Check if a mapped step's message signals completion */
export function isCompletionMessage(step: ThinkingStepType, message: string): boolean {
  switch (step) {
    case 'guardrail':
      return message.startsWith('Query is')
    case 'out_of_scope':
      return message.startsWith('Generating out-of-scope')
    case 'routing':
      return message.startsWith('Decided to')
    case 'executing':
      return message.endsWith(' completed') || message.endsWith(' failed')
    case 'grading':
      return message.startsWith('Found ')
    case 'generation':
      return message === 'Generation complete'
    default:
      return false
  }
}

/** Check if a raw backend step+message should be dropped before processing */
export function isSkippableMessage(rawStep: string, message: string): boolean {
  if (rawStep !== 'executing') return false
  return message.startsWith('Executing tool') || message.startsWith('Executed ')
}

/** Extract tool name from "Calling {tool}..." messages */
export function extractToolName(message: string): string | undefined {
  const match = message.match(/^Calling ([\w-]+)/)
  return match?.[1]
}

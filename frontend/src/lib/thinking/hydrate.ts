import type { PersistedThinkingStep, ThinkingStep, ThinkingStepType } from '../../types/api'
import { generateStepId } from '../../utils/id'
import { STEP_CONFIG } from './constants'

const VALID_STEPS = new Set<string>(Object.keys(STEP_CONFIG))

/**
 * Convert persisted thinking steps from the backend into ThinkingStep[]
 * for rendering in StepActivityFeed on history load.
 */
export function hydrateThinkingSteps(
  persisted: PersistedThinkingStep[] | null | undefined
): ThinkingStep[] | undefined {
  if (!persisted?.length) return undefined

  return persisted.map((p) => {
    const stepType: ThinkingStepType = VALID_STEPS.has(p.step)
      ? (p.step as ThinkingStepType)
      : 'executing'

    return {
      id: generateStepId(),
      step: stepType,
      message: p.message,
      details: p.details ?? undefined,
      status: 'complete' as const,
      timestamp: new Date(p.started_at),
      startTime: new Date(p.started_at),
      endTime: new Date(p.completed_at),
      order: STEP_CONFIG[stepType].order,
      toolName: p.tool_name ?? undefined,
    }
  })
}

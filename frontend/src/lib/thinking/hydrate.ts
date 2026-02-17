import type {
  PersistedThinkingStep,
  ThinkingStep,
  ActivityStep,
  InternalStep,
} from '../../types/api'
import { generateStepId } from '../../utils/id'
import { TOOL_TO_KIND, TOOL_LABELS, INTERNAL_LABELS, INTERNAL_STEP_NAMES } from './constants'
import { mapStepType } from './stepMapping'
import { humanizeToolName } from '../../utils/formatting'

/**
 * Convert persisted thinking steps from the backend into ThinkingStep[]
 * for rendering in ThinkingTimeline on history load.
 */
export function hydrateThinkingSteps(
  persisted: PersistedThinkingStep[] | null | undefined
): ThinkingStep[] | undefined {
  if (!persisted?.length) return undefined

  return persisted.map((p): ThinkingStep => {
    const toolName = p.tool_name ?? undefined
    const startTime = new Date(p.started_at)
    const endTime = new Date(p.completed_at)
    const details = p.details ?? undefined

    // Tool-bearing steps -> ActivityStep (mapped tool_name, or executing with tool_name)
    if (toolName && (TOOL_TO_KIND[toolName] || p.step === 'executing')) {
      const kind = TOOL_TO_KIND[toolName] ?? 'retrieve'
      const label = TOOL_LABELS[toolName]?.label ?? humanizeToolName(toolName)
      return {
        id: generateStepId(),
        kind,
        toolName,
        label,
        message: p.message,
        details,
        status: 'complete',
        startTime,
        endTime,
        isInternal: false,
      } satisfies ActivityStep
    }

    // Internal steps
    if (INTERNAL_STEP_NAMES.has(p.step)) {
      const kind = mapStepType(p.step)
      return {
        id: generateStepId(),
        kind,
        label: INTERNAL_LABELS[kind],
        message: p.message,
        details,
        status: 'complete',
        startTime,
        endTime,
        isInternal: true,
      } satisfies InternalStep
    }

    // Fallback: unknown step -> InternalStep with kind "executing"
    return {
      id: generateStepId(),
      kind: 'executing',
      label: INTERNAL_LABELS.executing,
      message: p.message,
      details,
      status: 'complete',
      startTime,
      endTime,
      isInternal: true,
    } satisfies InternalStep
  })
}

import type { StatusEventData, ActivityStep, InternalStep, InternalStepKind } from '../../types/api'
import { TOOL_LABELS, TOOL_TO_KIND, INTERNAL_LABELS, INTERNAL_STEP_NAMES } from './constants'
import { generateStepId } from '../../utils/id'
import { humanizeToolName } from '../../utils/formatting'

const warnedTools = new Set<string>()

function warnUnmappedTool(toolName: string): void {
  if (warnedTools.has(toolName)) return
  warnedTools.add(toolName)
  console.warn(`[thinking] Unmapped tool "${toolName}" -- add it to TOOL_LABELS and TOOL_TO_KIND`)
}

export function isToolStartEvent(data: StatusEventData): boolean {
  return data.step === 'executing'
    && !!data.details?.tool_name
    && data.details?.success === undefined
}

export function isToolEndEvent(data: StatusEventData): boolean {
  return data.step === 'executing'
    && !!data.details?.tool_name
    && data.details?.success !== undefined
}

export function isRetryEvent(data: StatusEventData): boolean {
  const iteration = data.details?.iteration
  return typeof iteration === 'number' && iteration > 1
}

function buildToolStartMessage(toolName: string, details?: Record<string, unknown>): string {
  const info = TOOL_LABELS[toolName]
  const base = info?.label ?? humanizeToolName(toolName)

  const args = details?.args as Record<string, unknown> | undefined
  if (args) {
    const query = args.query ?? args.search_query ?? args.arxiv_id
    if (typeof query === 'string' && query.length > 0) {
      const truncated = query.length > 60 ? query.slice(0, 57) + '...' : query
      return `${base} for "${truncated}"...`
    }
  }

  return `${base}...`
}

export function buildToolEndMessage(
  toolName: string,
  success: boolean,
  resultSummary?: string
): string {
  const info = TOOL_LABELS[toolName]
  const verb = info?.pastVerb ?? humanizeToolName(toolName)

  if (!success) {
    return `${verb} -- failed`
  }

  if (resultSummary) {
    return `${verb} -- ${resultSummary}`
  }

  return `${verb} -- done`
}

export function createActivityStep(data: StatusEventData): ActivityStep {
  const toolName = (data.details?.tool_name as string) ?? ''
  const kind = TOOL_TO_KIND[toolName] ?? 'retrieve'
  const label = TOOL_LABELS[toolName]?.label ?? humanizeToolName(toolName)

  if (!TOOL_LABELS[toolName]) warnUnmappedTool(toolName)

  return {
    id: generateStepId(),
    kind,
    toolName,
    label,
    message: buildToolStartMessage(toolName, data.details),
    details: data.details,
    status: 'running',
    startTime: new Date(),
    isInternal: false,
  }
}

export function mapStepType(step: string): InternalStepKind {
  return INTERNAL_STEP_NAMES.has(step) ? (step as InternalStepKind) : 'executing'
}

export function createInternalStep(data: StatusEventData): InternalStep {
  const kind = mapStepType(data.step)

  return {
    id: generateStepId(),
    kind,
    label: INTERNAL_LABELS[kind],
    message: data.message,
    details: data.details,
    status: 'running',
    startTime: new Date(),
    isInternal: true,
  }
}

export function createRefiningStep(data: StatusEventData): ActivityStep {
  const now = new Date()
  return {
    id: generateStepId(),
    kind: 'refining',
    toolName: '',
    label: 'Refining search query',
    message: 'Refining search query...',
    details: data.details,
    status: 'complete',
    startTime: now,
    endTime: now,
    isInternal: false,
  }
}

export function isInternalStepName(step: string): boolean {
  return INTERNAL_STEP_NAMES.has(step)
}

import type { StatusEventData } from '../../types/api'

export const COMPLETION_PATTERNS: Record<string, RegExp[]> = {
  guardrail: [/is (in|out of) scope/i, /passed|failed/i],
  routing: [/decided to/i, /routing to/i],
  executing: [/executed|completed|failed|retrieved|found/i],
  grading: [/found \d+ relevant/i, /graded|relevant/i],
  generation: [/complete|finished/i],
  out_of_scope: [/out of scope/i],
  confirming: [/confirmed|declined|approved|skipped/i],
  ingesting: [/ingested|complete|finished|failed/i],
}

function isCompletionMessage(step: string, message: string): boolean {
  const patterns = COMPLETION_PATTERNS[step]
  return patterns?.some((re) => re.test(message)) ?? false
}

export function isInternalCompletion(data: StatusEventData): boolean {
  return isCompletionMessage(data.step, data.message)
}

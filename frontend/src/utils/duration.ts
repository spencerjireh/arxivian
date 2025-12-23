import type { ThinkingStep } from '../types/api'

export function getStepDuration(step: ThinkingStep): number {
  if (!step.endTime) {
    return Date.now() - step.startTime.getTime()
  }
  return step.endTime.getTime() - step.startTime.getTime()
}

export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${Math.round(ms)}ms`
  }
  return `${(ms / 1000).toFixed(1)}s`
}

export function calculateTotalDuration(steps: ThinkingStep[]): number {
  if (steps.length === 0) return 0

  const firstStart = Math.min(...steps.map((s) => s.startTime.getTime()))
  const lastEnd = Math.max(...steps.map((s) => (s.endTime?.getTime() ?? s.startTime.getTime())))
  return lastEnd - firstStart
}

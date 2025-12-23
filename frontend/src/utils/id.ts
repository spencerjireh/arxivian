export function generateId(prefix?: string): string {
  const timestamp = Date.now()
  const random = Math.random().toString(36).slice(2, 9)
  return prefix ? `${prefix}-${timestamp}-${random}` : `${timestamp}-${random}`
}

export function generateStepId(): string {
  return generateId('step')
}

export function generateMessageId(): string {
  return generateId()
}

export interface FormattingOptions {
  maxStringLength?: number
  maxArrayItems?: number
}

export function formatDetailKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim()
}

export function formatDetailValue(
  key: string,
  value: unknown,
  options: FormattingOptions = {}
): string {
  const { maxStringLength = 80, maxArrayItems } = options

  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') {
    if (key.includes('score') || key.includes('threshold')) {
      return `${value}%`
    }
    return value.toString()
  }
  if (typeof value === 'string') {
    return value.length > maxStringLength ? `${value.slice(0, maxStringLength)}...` : value
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '-'
    if (maxArrayItems && value.length > maxArrayItems) {
      return value.slice(0, maxArrayItems).join(', ') + '...'
    }
    return value.join(', ')
  }
  return JSON.stringify(value)
}

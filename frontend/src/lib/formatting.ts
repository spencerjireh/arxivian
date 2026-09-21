// Display formatting for author lists and dates.
export function formatAuthors(authors: string[]): string {
  if (authors.length <= 3) return authors.join(', ')
  return `${authors.slice(0, 3).join(', ')} +${authors.length - 3} more`
}

/** "Jan 1, 2024" */
export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

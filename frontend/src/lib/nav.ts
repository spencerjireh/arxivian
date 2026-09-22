// Top-nav active-item matching and the validated post-sign-in return path.

/** Which nav item a pathname belongs to; paper detail pages (and the legacy /feed) count as the feed. */
export function matchesNav(path: string, pathname: string): boolean {
  if (path === '/') {
    return pathname === '/' || pathname.startsWith('/papers') || pathname.startsWith('/feed')
  }
  return pathname === path
}

/**
 * The page to return to after sign-in, read from `location.state.from` (a path string or a
 * router Location). Only a same-origin absolute path is accepted, so a crafted `//host`
 * cannot redirect off-site; anything else falls back to the feed.
 */
export function returnPathFrom(state: unknown): string {
  if (typeof state !== 'object' || state === null || !('from' in state)) return '/'
  const from: unknown = state.from
  let path: string | undefined
  if (typeof from === 'string') {
    path = from
  } else if (typeof from === 'object' && from !== null && 'pathname' in from) {
    const loc = from as { pathname: unknown; search?: unknown }
    if (typeof loc.pathname === 'string') {
      path = loc.pathname + (typeof loc.search === 'string' ? loc.search : '')
    }
  }
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) return '/'
  return path
}

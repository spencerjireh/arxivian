// Sidebar active-item matching for a pathname.
/** Which sidebar nav item a pathname belongs to; paper detail pages count as the feed. */
export function matchesNav(path: string, pathname: string): boolean {
  if (path === '/feed') return pathname.startsWith('/feed') || pathname.startsWith('/papers')
  return pathname === path
}

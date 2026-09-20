// Heading components with GitHub-style slugs so in-document anchors work (privacy page).
import { createElement, type ReactNode } from 'react'
import type { Components } from 'react-markdown'

/** GitHub-style heading slug so a document's own `[text](#slug)` links resolve. */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

function textOf(node: ReactNode): string {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (node && typeof node === 'object' && 'props' in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children)
  }
  return ''
}

/** Component overrides that give h1-h3 an `id` (and a scroll margin under the sticky header). */
export function headingComponents(base: Components): Components {
  const withId = (tag: 'h1' | 'h2' | 'h3', className: string) => {
    return ({ children }: { children?: ReactNode }) =>
      createElement(tag, { id: slugify(textOf(children)), className }, children)
  }
  return {
    ...base,
    h1: withId('h1', 'font-display text-4xl sm:text-5xl text-stone-900 tracking-tight mb-4'),
    h2: withId('h2', 'scroll-mt-24 font-display text-lg font-semibold text-stone-900 mt-10 mb-3'),
    h3: withId('h3', 'scroll-mt-24 font-medium text-stone-800 mt-6 mb-2'),
  }
}

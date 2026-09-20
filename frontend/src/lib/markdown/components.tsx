import { ExternalLink } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Components } from 'react-markdown'

/** react-markdown passes code content as a string or an array of strings. */
export function codeText(children: ReactNode): string {
  const text = Array.isArray(children)
    ? children.join('')
    : typeof children === 'string'
      ? children
      : ''
  return text.replace(/\n$/, '')
}

export const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="font-display mt-6 mb-4 text-2xl leading-tight text-stone-900 first:mt-0">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="font-display mt-5 mb-3 text-xl leading-tight text-stone-900 first:mt-0">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="font-display mt-4 mb-2 text-lg leading-snug text-stone-900 first:mt-0">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="mt-4 mb-2 text-base font-medium text-stone-900 first:mt-0">{children}</h4>
  ),
  h5: ({ children }) => (
    <h5 className="mt-3 mb-1.5 text-sm font-medium text-stone-900 first:mt-0">{children}</h5>
  ),
  h6: ({ children }) => (
    <h6 className="mt-3 mb-1 text-xs font-medium tracking-wide text-stone-700 uppercase first:mt-0">
      {children}
    </h6>
  ),

  p: ({ children }) => <p className="mb-4 leading-relaxed text-stone-700 last:mb-0">{children}</p>,

  a: ({ href, children }) => {
    const isArxiv = href?.includes('arxiv.org/abs/')
    if (isArxiv) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-1.5 py-0.5 font-mono text-xs text-amber-700 no-underline transition-colors duration-150 hover:bg-amber-100"
        >
          {children}
          <ExternalLink className="h-2.5 w-2.5 flex-shrink-0 text-amber-400" strokeWidth={1.5} />
        </a>
      )
    }
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-0.5 text-stone-900 underline decoration-stone-300 underline-offset-2 transition-colors duration-150 hover:decoration-stone-500"
      >
        {children}
        <ExternalLink className="h-3 w-3 flex-shrink-0 text-stone-400" strokeWidth={1.5} />
      </a>
    )
  },

  ul: ({ children }) => <ul className="mb-4 list-none space-y-1.5 pl-0 last:mb-0">{children}</ul>,
  ol: ({ children }) => (
    <ol className="counter-reset-list mb-4 list-none space-y-1.5 pl-0 last:mb-0">{children}</ol>
  ),
  li: ({ children, ...props }) => {
    const isOrdered = props.node?.position?.start.column === 1
    return (
      <li className="flex gap-2 leading-relaxed text-stone-700">
        <span className="flex-shrink-0 text-stone-400 select-none">{isOrdered ? '' : '-'}</span>
        <span>{children}</span>
      </li>
    )
  },

  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-2 border-stone-200 pl-4 text-stone-600 italic">
      {children}
    </blockquote>
  ),

  // Plain code blocks; MarkdownBody swaps in the syntax highlighter for chat.
  code: (props) => {
    const { children, className, node, ...rest } = props
    const isBlock = !!node?.position && /language-/.test(className || '')
    return isBlock ? (
      <pre className="my-4 overflow-x-auto rounded-xl bg-[#282c34] p-4 text-sm text-stone-200">
        <code>{codeText(children)}</code>
      </pre>
    ) : (
      <code
        className="rounded bg-stone-100 px-1.5 py-0.5 font-mono text-sm text-stone-800"
        {...rest}
      >
        {children}
      </code>
    )
  },

  // remark-math / rehype-katex wrappers
  div: ({ className, children, ...props }) => {
    if (className === 'math math-display') {
      return (
        <div className="math-display my-6 overflow-x-auto overflow-y-hidden" {...props}>
          {children}
        </div>
      )
    }
    return (
      <div className={className} {...props}>
        {children}
      </div>
    )
  },
  span: ({ className, children, ...props }) => {
    if (className === 'math math-inline') {
      return (
        <span className="math-inline text-stone-800" {...props}>
          {children}
        </span>
      )
    }
    return (
      <span className={className} {...props}>
        {children}
      </span>
    )
  },

  table: ({ children }) => (
    <div className="my-4 overflow-x-auto">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="border-b border-stone-200">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-stone-100">{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => (
    <th className="px-4 py-2.5 text-left text-xs font-medium tracking-wide text-stone-500 uppercase">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="px-4 py-2.5 align-top text-stone-700">{children}</td>,

  hr: () => <hr className="my-6 border-t border-stone-200" />,

  strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,

  del: ({ children }) => <del className="text-stone-500 line-through">{children}</del>,

  pre: ({ children }) => <>{children}</>,
}

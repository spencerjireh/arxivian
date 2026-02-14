import type { Components } from 'react-markdown'
import type { PluggableList } from 'unified'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

export const remarkPlugins: PluggableList = [remarkMath, remarkGfm]

export const rehypePlugins: PluggableList = [rehypeKatex]

export const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '')
    const codeString = String(children).replace(/\n$/, '')

    if (match) {
      return (
        <div className="relative rounded-lg overflow-hidden my-4 border border-stone-200">
          <div className="flex items-center justify-between px-4 py-2 bg-stone-100 border-b border-stone-200">
            <span className="text-xs font-mono text-stone-500">{match[1]}</span>
          </div>
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            customStyle={{
              margin: 0,
              borderRadius: 0,
              background: '#1c1917',
              fontSize: '0.875rem',
            }}
            {...props}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      )
    }

    return (
      <code
        className="px-1.5 py-0.5 rounded bg-stone-100 text-stone-800 text-sm font-mono"
        {...props}
      >
        {children}
      </code>
    )
  },

  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-stone-700 underline underline-offset-2 hover:text-stone-900"
        {...props}
      >
        {children}
      </a>
    )
  },

  table({ children, ...props }) {
    return (
      <div className="overflow-x-auto my-4">
        <table className="min-w-full border border-stone-200 rounded-lg" {...props}>
          {children}
        </table>
      </div>
    )
  },

  thead({ children, ...props }) {
    return (
      <thead className="bg-stone-50" {...props}>
        {children}
      </thead>
    )
  },

  th({ children, ...props }) {
    return (
      <th
        className="px-4 py-2 text-left text-xs font-medium text-stone-500 uppercase tracking-wider border-b border-stone-200"
        {...props}
      >
        {children}
      </th>
    )
  },

  td({ children, ...props }) {
    return (
      <td className="px-4 py-2 text-sm text-stone-700 border-b border-stone-100" {...props}>
        {children}
      </td>
    )
  },

  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="border-l-2 border-stone-300 pl-4 my-4 text-stone-600 italic"
        {...props}
      >
        {children}
      </blockquote>
    )
  },

  p({ children, ...props }) {
    return (
      <p className="mb-4 leading-relaxed" {...props}>
        {children}
      </p>
    )
  },

  ul({ children, ...props }) {
    return (
      <ul className="list-disc pl-6 mb-4 space-y-1" {...props}>
        {children}
      </ul>
    )
  },

  ol({ children, ...props }) {
    return (
      <ol className="list-decimal pl-6 mb-4 space-y-1" {...props}>
        {children}
      </ol>
    )
  },

  li({ children, ...props }) {
    return (
      <li className="text-stone-700 leading-relaxed" {...props}>
        {children}
      </li>
    )
  },

  h1({ children, ...props }) {
    return (
      <h1 className="text-2xl font-semibold text-stone-900 mt-6 mb-3" {...props}>
        {children}
      </h1>
    )
  },

  h2({ children, ...props }) {
    return (
      <h2 className="text-xl font-semibold text-stone-900 mt-5 mb-2" {...props}>
        {children}
      </h2>
    )
  },

  h3({ children, ...props }) {
    return (
      <h3 className="text-lg font-medium text-stone-900 mt-4 mb-2" {...props}>
        {children}
      </h3>
    )
  },

  hr() {
    return <hr className="my-6 border-stone-200" />
  },
}

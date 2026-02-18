import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import type { PluggableList } from 'unified'

export const remarkPlugins: PluggableList = [remarkGfm, remarkMath]

export const rehypePlugins: PluggableList = [
  [
    rehypeKatex,
    {
      strict: false,
      trust: false,
      output: 'html',
      fleqn: false,
      throwOnError: false,
      errorColor: '#B91C1C',
      macros: {
        '\\RR': '\\mathbb{R}',
        '\\NN': '\\mathbb{N}',
        '\\ZZ': '\\mathbb{Z}',
        '\\QQ': '\\mathbb{Q}',
        '\\CC': '\\mathbb{C}',
      },
    },
  ],
]

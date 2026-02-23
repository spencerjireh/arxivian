import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import type { PluggableList } from 'unified'
import { remarkArxivLinks } from './remark-arxiv-links'

export const remarkPlugins: PluggableList = [remarkGfm, remarkMath, remarkArxivLinks]

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

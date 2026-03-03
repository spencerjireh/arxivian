import remarkGfm from 'remark-gfm'
import type { PluggableList } from 'unified'
import { remarkArxivLinks } from './remark-arxiv-links'

export const remarkPluginsBase: PluggableList = [remarkGfm, remarkArxivLinks]

export const rehypePluginsBase: PluggableList = []

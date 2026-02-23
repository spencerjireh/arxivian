/**
 * Remark plugin that auto-links arXiv paper IDs to arxiv.org.
 *
 * Operates on the MDAST so code blocks, inline code, and existing links
 * are skipped automatically via mdast-util-find-and-replace's ignore list.
 *
 * Supported formats:
 *   [2301.12345]          -- bracketed standard ID
 *   [cs/0112017]          -- bracketed legacy ID
 *   arXiv:2301.12345      -- colon-prefixed standard ID (case-insensitive)
 *   arXiv:cs/0112017      -- colon-prefixed legacy ID
 */
import type { Root, PhrasingContent } from 'mdast'
import { findAndReplace } from 'mdast-util-find-and-replace'

const ARXIV_URL = 'https://arxiv.org/abs/'

// Standard ID: YYMM.NNNNN (4- or 5-digit suffix)
const STANDARD_ID = /\d{4}\.\d{4,5}/

// Legacy ID: category/YYMMNNN (e.g. cs/0112017, hep-th/9901001)
const LEGACY_ID = /[a-z][\w-]*\/\d{7}/

// Combined ID pattern (non-capturing alternation)
const ID_PATTERN = `(?:${STANDARD_ID.source}|${LEGACY_ID.source})`

// Bracketed: [2301.12345] or [cs/0112017]
const BRACKETED_RE = new RegExp(`\\[(${ID_PATTERN})\\]`, 'g')

// Colon-prefixed: arXiv:2301.12345 or arXiv:cs/0112017 (case-insensitive prefix)
const COLON_RE = new RegExp(`arXiv:(${ID_PATTERN})`, 'gi')

function buildLink(id: string, display: string): PhrasingContent {
  return {
    type: 'link',
    url: `${ARXIV_URL}${id}`,
    children: [{ type: 'text', value: display }],
  }
}

export function remarkArxivLinks() {
  return (tree: Root) => {
    findAndReplace(tree, [
      [BRACKETED_RE, (_match: string, id: string) => buildLink(id, id)],
      [COLON_RE, (match: string, id: string) => buildLink(id, match)],
    ])
  }
}

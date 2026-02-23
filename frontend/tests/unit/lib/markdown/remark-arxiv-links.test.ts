import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkStringify from 'remark-stringify'
import { remarkArxivLinks } from '../../../../src/lib/markdown/remark-arxiv-links'

/** Run markdown through the plugin and return the result string. */
async function process(md: string): Promise<string> {
  const result = await unified()
    .use(remarkParse)
    .use(remarkArxivLinks)
    .use(remarkStringify)
    .process(md)
  return String(result)
}

// ---------------------------------------------------------------------------
// Bracketed IDs
// ---------------------------------------------------------------------------

describe('bracketed arXiv IDs', () => {
  it('converts standard ID [YYMM.NNNNN] to link', async () => {
    const out = await process('See [2301.12345] for details')
    expect(out).toContain('[2301.12345](https://arxiv.org/abs/2301.12345)')
  })

  it('converts 4-digit suffix [YYMM.NNNN]', async () => {
    const out = await process('Paper [1706.3762]')
    expect(out).toContain('[1706.3762](https://arxiv.org/abs/1706.3762)')
  })

  it('converts legacy category ID [cs/0112017]', async () => {
    const out = await process('[cs/0112017]')
    expect(out).toContain('[cs/0112017](https://arxiv.org/abs/cs/0112017)')
  })

  it('converts legacy ID with hyphenated category [hep-th/9901001]', async () => {
    const out = await process('[hep-th/9901001]')
    expect(out).toContain('[hep-th/9901001](https://arxiv.org/abs/hep-th/9901001)')
  })
})

// ---------------------------------------------------------------------------
// Colon-prefixed IDs
// ---------------------------------------------------------------------------

describe('colon-prefixed arXiv IDs', () => {
  it('converts arXiv:YYMM.NNNNN to link', async () => {
    const out = await process('See arXiv:2301.12345 for details')
    expect(out).toContain('[arXiv:2301.12345](https://arxiv.org/abs/2301.12345)')
  })

  it('is case-insensitive (ARXIV:, Arxiv:)', async () => {
    const out = await process('ARXIV:2301.12345 and Arxiv:1706.3762')
    expect(out).toContain('(https://arxiv.org/abs/2301.12345)')
    expect(out).toContain('(https://arxiv.org/abs/1706.3762)')
  })

  it('converts arXiv:category/YYMMNNN to link', async () => {
    const out = await process('arXiv:cs/0112017')
    expect(out).toContain('[arXiv:cs/0112017](https://arxiv.org/abs/cs/0112017)')
  })
})

// ---------------------------------------------------------------------------
// Nodes that should be skipped
// ---------------------------------------------------------------------------

describe('ignored contexts', () => {
  it('does not touch IDs inside inline code', async () => {
    const out = await process('Use `[2301.12345]` to cite')
    expect(out).toContain('`[2301.12345]`')
    expect(out).not.toContain('arxiv.org')
  })

  it('does not touch IDs inside code blocks', async () => {
    const out = await process('```\n[2301.12345]\n```')
    expect(out).not.toContain('arxiv.org')
  })

  it('does not touch IDs inside existing links', async () => {
    const out = await process('[click here](https://example.com/2301.12345)')
    expect(out).not.toContain('arxiv.org')
  })
})

// ---------------------------------------------------------------------------
// Multiple matches and edge cases
// ---------------------------------------------------------------------------

describe('edge cases', () => {
  it('converts multiple IDs on one line', async () => {
    const out = await process('[1812.00660] and [2301.12345]')
    expect(out).toContain('(https://arxiv.org/abs/1812.00660)')
    expect(out).toContain('(https://arxiv.org/abs/2301.12345)')
  })

  it('handles mixed bracketed and colon-prefixed', async () => {
    const out = await process('[1812.00660] and arXiv:2301.12345')
    expect(out).toContain('(https://arxiv.org/abs/1812.00660)')
    expect(out).toContain('(https://arxiv.org/abs/2301.12345)')
  })

  it('does not match plain bracketed numbers like [42]', async () => {
    const out = await process('See [42] or [section 3]')
    expect(out).not.toContain('arxiv.org')
  })

  it('leaves plain text unchanged', async () => {
    const out = await process('Just regular text.')
    expect(out.trim()).toBe('Just regular text.')
  })

  it('handles empty string', async () => {
    const out = await process('')
    expect(out.trim()).toBe('')
  })
})

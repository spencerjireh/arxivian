import { render } from '@testing-library/react'
import MarkdownBody from '../../../../src/components/chat/MarkdownBody'

describe('MarkdownBody', () => {
  it('renders math from dollar and paren delimiters', () => {
    const { container } = render(<MarkdownBody content={'Inline $x^2$ and \\(y_i\\).'} />)
    expect(container.querySelectorAll('.katex').length).toBe(2)
  })

  it('renders GFM tables and arXiv ids as links', () => {
    const { container } = render(
      <MarkdownBody content={'| a | b |\n|---|---|\n| 1 | 2 |\n\nSee [2301.00001].'} />
    )
    expect(container.querySelector('table')).not.toBeNull()
    expect(container.querySelector('a[href*="2301.00001"]')).not.toBeNull()
  })
})

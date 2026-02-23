import { preprocessLatex } from '../../../../src/lib/markdown/preprocessors'

describe('preprocessLatex', () => {
  it('converts inline \\(...\\) to $...$', () => {
    expect(preprocessLatex('The loss \\(L_{KD}\\) is defined as')).toBe(
      'The loss $L_{KD}$ is defined as',
    )
  })

  it('converts display \\[...\\] to $$...$$', () => {
    expect(preprocessLatex('\\[E = mc^2\\]')).toBe('$$E = mc^2$$')
  })

  it('handles multiple inline matches on one line', () => {
    expect(preprocessLatex('\\(a\\) and \\(b\\)')).toBe('$a$ and $b$')
  })

  it('handles multiline display math', () => {
    const input = '\\[\nx^2 +\ny^2\n\\]'
    expect(preprocessLatex(input)).toBe('$$\nx^2 +\ny^2\n$$')
  })

  it('does not convert escaped backslashes \\\\(', () => {
    expect(preprocessLatex('\\\\(not math\\\\)')).toBe('\\\\(not math\\\\)')
  })

  it('leaves content without LaTeX delimiters unchanged', () => {
    const plain = 'No math here, just text.'
    expect(preprocessLatex(plain)).toBe(plain)
  })

  it('preserves existing dollar-sign math', () => {
    const input = 'Already $x^2$ and $$y^2$$'
    expect(preprocessLatex(input)).toBe(input)
  })

  it('handles empty string', () => {
    expect(preprocessLatex('')).toBe('')
  })
})

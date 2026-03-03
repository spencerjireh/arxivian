/**
 * Content sniffing to decide whether a message needs the enhanced markdown
 * renderer (KaTeX math + syntax-highlighted code blocks).
 *
 * Intentionally cheap -- runs on every render of MarkdownRenderer, so it
 * must be a fast string scan, not a full parse.
 */

// Matches $ ... $ (inline math), $$ ... $$ (display math),
// \( ... \), \[ ... \] (LaTeX delimiters before preprocessing)
const MATH_PATTERN = /\$\$?[^$]+\$\$?|(?<!\\)\\\(|(?<!\\)\\\[/

// Matches fenced code blocks: ``` with an optional language tag
const CODE_FENCE_PATTERN = /^```\w*/m

export function needsEnhancedRenderer(content: string): boolean {
  return MATH_PATTERN.test(content) || CODE_FENCE_PATTERN.test(content)
}

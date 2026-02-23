/**
 * Text preprocessors that normalize content before it reaches ReactMarkdown.
 *
 * Runs as plain string transforms -- no AST manipulation, no plugin coupling.
 */

/**
 * Convert LaTeX delimiters from \(...\) / \[...\] to $...$ / $$...$$.
 *
 * remark-math only recognises dollar-sign delimiters, but LLMs frequently
 * emit the parenthesis/bracket form. Negative lookbehind skips escaped
 * backslashes (\\( is literal text, not a delimiter).
 */
export function preprocessLatex(content: string): string {
  // Inline: \( ... \)  ->  $ ... $
  content = content.replace(/(?<!\\)\\\((.+?)\\\)/g, (_match, expr: string) => `$${expr}$`)

  // Display: \[ ... \]  ->  $$ ... $$   (dotAll for multiline)
  content = content.replace(/(?<!\\)\\\[(.+?)\\\]/gs, (_match, expr: string) => `$$${expr}$$`)

  return content
}

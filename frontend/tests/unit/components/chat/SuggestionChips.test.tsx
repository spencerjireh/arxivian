import { render, screen, fireEvent } from '@testing-library/react'
import { BookOpen } from 'lucide-react'
import SuggestionChips from '../../../../src/components/chat/SuggestionChips'

describe('SuggestionChips', () => {
  it('renders the default list', () => {
    render(<SuggestionChips onSelect={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Summarize a paper/ })).toBeInTheDocument()
    expect(screen.getAllByRole('button')).toHaveLength(4)
  })

  it('renders a custom list and reports the prompt', () => {
    const onSelect = vi.fn()
    render(
      <SuggestionChips
        onSelect={onSelect}
        columns={1}
        suggestions={[{ icon: BookOpen, title: 'Custom', prompt: 'Custom prompt.' }]}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /Custom/ }))
    expect(onSelect).toHaveBeenCalledWith('Custom prompt.')
    expect(screen.getAllByRole('button')).toHaveLength(1)
  })
})

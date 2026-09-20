import { useState } from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import FeedProfileForm from '../../../../src/components/onboarding/FeedProfileForm'
import KeywordInput from '../../../../src/components/onboarding/KeywordInput'

function mountForm(initialValue?: Parameters<typeof FeedProfileForm>[0]['initialValue']) {
  const onSubmit = vi.fn()
  render(
    <FeedProfileForm
      initialValue={initialValue}
      onSubmit={onSubmit}
      isSubmitting={false}
      submitLabel="Build my feed"
    />
  )
  return onSubmit
}

describe('FeedProfileForm', () => {
  it('blocks submit until a category and a compute profile are chosen', () => {
    const onSubmit = mountForm()
    fireEvent.click(screen.getByRole('button', { name: 'Build my feed' }))
    expect(screen.getByText('Pick at least one category')).toBeInTheDocument()
    expect(screen.getByText('Choose your compute setup')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: /cs\.LG/ }))
    fireEvent.click(screen.getByRole('radio', { name: /Single GPU/ }))
    expect(screen.queryByText('Pick at least one category')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Build my feed' }))
    expect(onSubmit).toHaveBeenCalledWith({
      categories: ['cs.LG'],
      compute_profile: 'single_gpu',
      keywords: [],
    })
  })

  it('pre-fills from the initial value and toggles categories off', () => {
    const onSubmit = mountForm({
      categories: ['cs.CV', 'cs.LG'],
      compute_profile: 'cloud',
      keywords: ['rag'],
    })
    expect(screen.getByRole('button', { name: /cs\.CV/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('radio', { name: /Cloud/ })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByText('rag')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /cs\.CV/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Build my feed' }))
    expect(onSubmit).toHaveBeenCalledWith({
      categories: ['cs.LG'],
      compute_profile: 'cloud',
      keywords: ['rag'],
    })
  })

  it('disables the submit button while submitting', () => {
    render(<FeedProfileForm onSubmit={vi.fn()} isSubmitting submitLabel="Save" />)
    expect(screen.getByRole('button', { name: '' })).toBeDisabled()
  })
})

describe('KeywordInput', () => {
  it('adds on Enter, lowercases, dedupes, caps at 10, and removes', () => {
    function Harness() {
      const [value, setValue] = useState<string[]>([])
      return <KeywordInput value={value} onChange={setValue} />
    }
    render(<Harness />)
    const input = screen.getByLabelText('Interest keyword')
    for (const k of ['RAG', 'rag', 'sparse', ' ', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']) {
      fireEvent.change(input, { target: { value: k } })
      fireEvent.keyDown(input, { key: 'Enter' })
    }
    expect(screen.getByText('rag')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Remove/ })).toHaveLength(10)
    expect(screen.queryByText('i')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove rag' }))
    expect(screen.queryByText('rag')).not.toBeInTheDocument()
  })
})

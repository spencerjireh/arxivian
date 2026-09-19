import { render, screen } from '@testing-library/react'
import SignalChips from '../../../../src/components/feed/SignalChips'
import ScoreBadge from '../../../../src/components/feed/ScoreBadge'

describe('SignalChips', () => {
  it('renders nothing when no signal is set', () => {
    const { container } = render(
      <SignalChips
        signals={{ pseudocode_present: false, public_datasets: false, single_gpu: false, code_released: false, compute_match: false }}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders code released and compute fit chips', () => {
    render(
      <SignalChips
        signals={{ pseudocode_present: false, public_datasets: false, single_gpu: false, code_released: true, compute_match: true }}
      />,
    )
    expect(screen.getByText('Code released')).toBeInTheDocument()
    expect(screen.getByText('Fits your compute')).toBeInTheDocument()
  })
})

describe('ScoreBadge', () => {
  it.each([
    [39, 'LOW'],
    [40, 'MED'],
    [69, 'MED'],
    [70, 'HIGH'],
  ])('bands %i as %s', (score, band) => {
    render(<ScoreBadge score={score} />)
    expect(screen.getByText(band)).toBeInTheDocument()
  })
})

import { screen, fireEvent, render } from '@testing-library/react'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import DistributionBar from '../../../../src/components/paper/DistributionBar'
import DimensionRow from '../../../../src/components/paper/DimensionRow'
import EvidenceList from '../../../../src/components/paper/EvidenceList'
import AttributeChips from '../../../../src/components/paper/AttributeChips'
import ScoreBreakdown from '../../../../src/components/paper/ScoreBreakdown'
import { makeDimension, makePaperScoreDetail } from '../../../fixtures/scores'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

describe('DistributionBar', () => {
  it('renders one segment per level and highlights the argmax', () => {
    render(<DistributionBar probabilities={{ '0': 0.1, '1': 0.3, '2': 0.6 }} level={2} maxLevel={2} labels={['Low', 'Med', 'High']} />)
    const bar = screen.getByRole('img')
    expect(bar).toHaveAttribute('aria-label', 'Low: 10%, Med: 30%, High: 60%')
    const segments = bar.querySelectorAll('[data-level]')
    expect(segments).toHaveLength(3)
    expect(segments[2]).toHaveAttribute('data-argmax', 'true')
    expect(segments[1]).not.toHaveAttribute('data-argmax')
    expect((segments[2] as HTMLElement).style.width).toBe('60%')
  })
})

describe('DimensionRow', () => {
  it('shows band, score, and a low-confidence chip below 0.5 only', () => {
    const { unmount } = render(<DimensionRow dimension={makeDimension({ confidence: 0.49 })} />)
    expect(screen.getByText('Method clarity')).toBeInTheDocument()
    expect(screen.getByText('HIGH')).toBeInTheDocument()
    expect(screen.getByText('80/100')).toBeInTheDocument()
    expect(screen.getByText('Low confidence')).toBeInTheDocument()
    unmount()
    render(<DimensionRow dimension={makeDimension({ confidence: 0.5 })} />)
    expect(screen.queryByText('Low confidence')).not.toBeInTheDocument()
  })

  it('toggles the evidence panel', () => {
    render(<DimensionRow dimension={makeDimension()} />)
    expect(screen.queryByText(/Algorithm 1/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { expanded: false }))
    expect(screen.getByText(/Algorithm 1/)).toBeInTheDocument()
    expect(screen.getByText('Algorithm or equations given')).toBeInTheDocument()
    expect(screen.getByText('3 of 4 criteria satisfied')).toBeInTheDocument()
  })
})

describe('EvidenceList', () => {
  it('renders pseudocode in a code block and other kinds as quotes with sources', () => {
    render(<EvidenceList evidence={makeDimension().evidence} />)
    const pre = screen.getByText(/Algorithm 1/)
    expect(pre.tagName).toBe('PRE')
    const quote = screen.getByText(/trained on 8 P100 GPUs/)
    expect(quote.tagName).toBe('BLOCKQUOTE')
    expect(screen.getByText('section 5')).toBeInTheDocument()
    expect(screen.getByText('Pseudocode and algorithm spans')).toBeInTheDocument()
  })

  it('says so when empty', () => {
    render(<EvidenceList evidence={[]} />)
    expect(screen.getByText(/No evidence quoted/)).toBeInTheDocument()
  })
})

describe('AttributeChips', () => {
  it('renders task, family and a code chip only when released', () => {
    const attrs = makePaperScoreDetail().attributes
    const { unmount } = render(<AttributeChips attributes={attrs} />)
    expect(screen.getByText('machine translation')).toBeInTheDocument()
    expect(screen.getByText('transformer')).toBeInTheDocument()
    expect(screen.getByText('Code released')).toBeInTheDocument()
    unmount()
    render(
      <AttributeChips
        attributes={{ ...attrs, code_released: { ...attrs.code_released!, answer: false }, task_type: { ...attrs.task_type!, answer: 'other' } }}
      />,
    )
    expect(screen.queryByText('Code released')).not.toBeInTheDocument()
    expect(screen.queryByText('other')).not.toBeInTheDocument()
  })
})

describe('ScoreBreakdown', () => {
  it('renders all four dimensions in order plus code mentions', () => {
    renderWithProviders(<ScoreBreakdown detail={makePaperScoreDetail()} />)
    const headings = ['Method clarity', 'Resource feasibility', 'Data availability', 'Demand']
    const rendered = screen
      .getAllByRole('button')
      .filter((b) => b.hasAttribute('aria-expanded'))
      .map((b) => b.textContent)
    headings.forEach((h, i) => expect(rendered[i]).toContain(h))
    expect(screen.getByText('Code released by the authors')).toBeInTheDocument()
    expect(screen.getByText(/tensor2tensor/)).toBeInTheDocument()
    expect(screen.getByLabelText('Score 71 of 100, high')).toBeInTheDocument()
  })
})

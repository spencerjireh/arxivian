import { screen, render, within } from '@testing-library/react'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import DistributionBar from '../../../../src/components/paper/DistributionBar'
import DimensionRow from '../../../../src/components/paper/DimensionRow'
import EvidenceList from '../../../../src/components/paper/EvidenceList'
import AttributeChips from '../../../../src/components/paper/AttributeChips'
import ScoreBreakdown from '../../../../src/components/paper/ScoreBreakdown'
import ScoringDetails from '../../../../src/components/paper/ScoringDetails'
import { makeDimension, makePaperScoreDetail } from '../../../fixtures/scores'

vi.mock('framer-motion', () => import('../../../mocks/framer-motion'))

describe('DistributionBar', () => {
  it('renders one segment per level and highlights the argmax', () => {
    render(
      <DistributionBar
        probabilities={{ '0': 0.1, '1': 0.3, '2': 0.6 }}
        level={2}
        maxLevel={2}
        labels={['Low', 'Med', 'High']}
      />
    )
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
  it('shows the band word, level label, plain facts and the evidence, always open', () => {
    render(<DimensionRow dimension={makeDimension()} />)
    const row = screen.getByRole('region', { name: 'Method clarity' })
    expect(within(row).getByText('Strong')).toBeInTheDocument()
    expect(within(row).getByText('3 criteria')).toBeInTheDocument()
    expect(within(row).getByText('Algorithm or equations given')).toBeInTheDocument()
    expect(within(row).getByText(/Algorithm 1/)).toBeInTheDocument()
    expect(within(row).queryByText('80/100')).not.toBeInTheDocument()
    expect(within(row).queryByText(/conf\./)).not.toBeInTheDocument()
    expect(within(row).queryByRole('button')).not.toBeInTheDocument()
  })

  it('reads Pass / Fail for the data gate', () => {
    render(
      <DimensionRow
        dimension={makeDimension({
          dimension: 'data_availability',
          level: 0,
          max_level: 1,
          band: 'LOW',
        })}
      />
    )
    expect(screen.getByText('Fail')).toBeInTheDocument()
  })
})

describe('ScoringDetails', () => {
  it('is closed by default and holds the rubric, confidence, distributions and judgments', () => {
    const detail = makePaperScoreDetail({ low_confidence: ['method_clarity'] })
    render(<ScoringDetails detail={detail} />)
    const details = screen.getByText('Scoring details').closest('details')
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/Rubric v2/)).toBeInTheDocument()
    expect(screen.getByText(/composite 71 of 100/)).toBeInTheDocument()
    expect(screen.getByText(/Low confidence on Method clarity/)).toBeInTheDocument()
    expect(screen.getByText('80/100')).toBeInTheDocument()
    expect(screen.getAllByText(/% conf\./)).toHaveLength(4)
    expect(screen.getAllByRole('img')).toHaveLength(4)
    expect(screen.getAllByText('Algorithm or equations given')).toHaveLength(4)
    expect(screen.getAllByTitle('yes 90% · no 10%')).toHaveLength(4)
    expect(screen.getAllByText('3 of 4 criteria satisfied')).toHaveLength(4)
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
        attributes={{
          ...attrs,
          code_released: { ...attrs.code_released!, answer: false },
          task_type: { ...attrs.task_type!, answer: 'other' },
        }}
      />
    )
    expect(screen.queryByText('Code released')).not.toBeInTheDocument()
    expect(screen.queryByText('other')).not.toBeInTheDocument()
  })
})

describe('ScoreBreakdown', () => {
  it('renders the summary, all four dimensions in order, code mentions and the closed details', () => {
    renderWithProviders(<ScoreBreakdown detail={makePaperScoreDetail({ compute_match: true })} />)
    expect(screen.getByText('Transformer for machine translation')).toBeInTheDocument()
    expect(
      screen.getByText('one datacenter GPU · public data · pseudocode given')
    ).toBeInTheDocument()
    expect(screen.getByText('Fits your compute')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Implementability meter' })).toBeInTheDocument()
    const regions = screen
      .getAllByRole('region')
      .map((r) => r.getAttribute('aria-label') ?? r.querySelector('h3')?.textContent)
    expect(regions).toEqual([
      'Score breakdown',
      'Method clarity',
      'Resource feasibility',
      'Data availability',
      'Demand',
    ])
    expect(screen.getByText('Code released by the authors')).toBeInTheDocument()
    expect(screen.getByText(/tensor2tensor/)).toBeInTheDocument()
    expect(screen.getByText('Scoring details').closest('details')).not.toHaveAttribute('open')
    expect(screen.queryByLabelText(/Score 71/)).not.toBeInTheDocument()
  })
})

import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../helpers/renderWithProviders'
import PrivacyPage from '../../../src/pages/PrivacyPage'

vi.mock('@clerk/clerk-react', () => import('../../mocks/clerk'))
vi.mock('../../../src/components/layout/PublicHeader', () => ({ default: () => <header /> }))
vi.mock('../../../src/components/layout/Footer', () => ({ default: () => <footer /> }))

describe('PrivacyPage', () => {
  it('renders the policy markdown with anchor ids the table of contents links to', () => {
    renderWithProviders(<PrivacyPage />)
    expect(screen.getByRole('heading', { level: 1, name: 'Privacy Policy' })).toBeInTheDocument()
    const section = screen.getByRole('heading', {
      level: 2,
      name: /1\. What Information Do We Collect\?/,
    })
    expect(section.id).toBe('1-what-information-do-we-collect')
    const tocLink = screen.getAllByRole('link', { name: 'What Information Do We Collect?' })[0]
    expect(tocLink).toHaveAttribute('href', '#1-what-information-do-we-collect')
  })
})

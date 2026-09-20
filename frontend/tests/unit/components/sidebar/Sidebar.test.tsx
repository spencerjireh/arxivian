import { screen } from '@testing-library/react'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import Sidebar from '../../../../src/components/sidebar/Sidebar'

vi.mock('@clerk/clerk-react', () => import('../../../mocks/clerk'))
vi.mock('../../../../src/components/sidebar/UserMenu', () => ({ default: () => <div>menu</div> }))

describe('Sidebar', () => {
  it('shows only Feed, Library and Settings', () => {
    renderWithProviders(<Sidebar />, { initialEntries: ['/feed'] })
    const labels = screen.getAllByRole('button').map((b) => b.textContent?.trim())
    expect(labels).toEqual(expect.arrayContaining(['Feed', 'Library', 'Settings']))
    expect(labels).not.toContain('Chat')
    expect(screen.queryByText(/New conversation/)).not.toBeInTheDocument()
  })

  it('marks the feed active on a paper detail page', () => {
    renderWithProviders(<Sidebar />, { initialEntries: ['/papers/2401.00001'] })
    const active = /(^|\s)text-stone-900(\s|$)/
    expect(screen.getByRole('button', { name: 'Feed' }).className).toMatch(active)
    expect(screen.getByRole('button', { name: 'Library' }).className).not.toMatch(active)
  })
})

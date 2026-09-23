import { screen, fireEvent } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import TopNav from '@/components/layout/TopNav'
import { renderWithProviders } from '../../../helpers/renderWithProviders'
import { mockSession, resetSession } from '../../../mocks/auth'

vi.mock('@/lib/auth', () => import('../../../mocks/auth'))

function renderNav(path = '/') {
  return renderWithProviders(
    <Routes>
      <Route path="*" element={<TopNav />} />
    </Routes>,
    { initialEntries: [path] }
  )
}

beforeEach(() => {
  resetSession()
})

describe('TopNav', () => {
  it('shows Feed, About, Pricing and a sign-in link with the return path when signed out', () => {
    renderNav('/papers/2401.00001')
    const links = screen.getAllByRole('link').map((l) => l.textContent?.trim())
    expect(links).toEqual(['Arxivian', 'Feed', 'About', 'Pricing', 'Sign in'])
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/sign-in')
    expect(screen.queryByRole('button', { name: 'Account menu' })).not.toBeInTheDocument()
  })

  it('marks the feed active on a paper detail page', () => {
    renderNav('/papers/2401.00001')
    expect(screen.getByRole('link', { name: 'Feed' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'About' })).not.toHaveAttribute('aria-current')
  })

  it('adds Library, Settings and the account menu when signed in', async () => {
    mockSession.isSignedIn = true
    renderNav('/settings')
    expect(screen.getByRole('link', { name: 'Library' })).toHaveAttribute('href', '/library')
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Account menu' }))
    expect(screen.getByText('Test User')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('menuitem', { name: /Sign out/ }))
    await vi.waitFor(() => expect(mockSession.signOut).toHaveBeenCalledTimes(1))
  })
})

// App shell for every routed page: top nav, the page (Outlet) in an error boundary, footer.
import { Outlet, useLocation } from 'react-router-dom'
import TopNav from './TopNav'
import Footer from './Footer'
import ErrorBoundary from '../ui/ErrorBoundary'
import PageErrorFallback from '../ui/PageErrorFallback'

/** A document page, not a fixed-height workspace: the window scrolls. */
const Layout = () => {
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-screen flex-col bg-[#FAFAF9]">
      <TopNav />
      <main className="flex flex-1 flex-col">
        <ErrorBoundary resetKey={pathname} fallback={(props) => <PageErrorFallback {...props} />}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Footer />
    </div>
  )
}

export default Layout

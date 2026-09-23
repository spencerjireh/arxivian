// Entry point: mounts <AppProvider><AppRouter/>; VITE_MAINTENANCE_MODE swaps in MaintenanceScreen.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import AppProvider from './app/provider'
import AppRouter from './app/router'
import MaintenanceScreen from './components/layout/MaintenanceScreen'

const root = createRoot(document.getElementById('root')!)

// Pivot maintenance curtain: render a standalone screen with no dependency on
// Clerk / router / query so it stays light and works even without those env vars.
if (import.meta.env.VITE_MAINTENANCE_MODE === 'true') {
  root.render(
    <StrictMode>
      <MaintenanceScreen />
    </StrictMode>
  )
} else {
  const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

  if (!CLERK_PUBLISHABLE_KEY) {
    throw new Error('Missing VITE_CLERK_PUBLISHABLE_KEY environment variable')
  }

  root.render(
    <StrictMode>
      <AppProvider clerkPublishableKey={CLERK_PUBLISHABLE_KEY}>
        <AppRouter />
      </AppProvider>
    </StrictMode>
  )
}

import logoIcon from '../assets/logo-icon.png'

/**
 * Full-screen curtain shown while the pivot is in progress. Rendered directly from main.tsx
 * (bypassing Clerk/router/query) when VITE_MAINTENANCE_MODE === 'true', so it stays light and
 * has no dependency on the rest of the app. On-brand with the Elegant Minimal design system.
 */
export default function MaintenanceScreen() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-[#FAFAF9] px-6 text-center">
      <div className="max-w-md">
        <img src={logoIcon} alt="Arxivian" className="mx-auto mb-8 h-12 w-12" />
        <p className="mb-5 text-xs tracking-[0.2em] text-stone-400 uppercase">Arxivian</p>
        <h1
          className="mb-6 text-4xl leading-tight text-stone-800 sm:text-5xl"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          We&rsquo;re rebuilding
          <br />
          something better
        </h1>
        <div className="mx-auto mb-6 h-px w-12 bg-stone-300" />
        <p className="leading-relaxed text-stone-500">
          Arxivian is being reimagined as a ranked feed of the papers most worth turning into
          software. We&rsquo;ll be back shortly.
        </p>
      </div>
      <p className="absolute bottom-8 text-xs tracking-wide text-stone-400">
        Thanks for your patience.
      </p>
    </div>
  )
}

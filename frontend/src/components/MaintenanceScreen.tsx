import logoIcon from '../assets/logo-icon.png'

/**
 * Full-screen curtain shown while the pivot is in progress. Rendered directly from main.tsx
 * (bypassing Clerk/router/query) when VITE_MAINTENANCE_MODE === 'true', so it stays light and
 * has no dependency on the rest of the app. On-brand with the Elegant Minimal design system.
 */
export default function MaintenanceScreen() {
  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[#FAFAF9] px-6 text-center">
      <div className="max-w-md">
        <img src={logoIcon} alt="Arxivian" className="w-12 h-12 mx-auto mb-8" />
        <p className="text-xs uppercase tracking-[0.2em] text-stone-400 mb-5">Arxivian</p>
        <h1
          className="text-4xl sm:text-5xl text-stone-800 mb-6 leading-tight"
          style={{ fontFamily: 'var(--font-display)' }}
        >
          We&rsquo;re rebuilding
          <br />
          something better
        </h1>
        <div className="w-12 h-px bg-stone-300 mx-auto mb-6" />
        <p className="text-stone-500 leading-relaxed">
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

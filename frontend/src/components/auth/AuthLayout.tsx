import logoIcon from '../../assets/logo-icon.png'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: React.ReactNode
}

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#FAFAF9] px-4">
      <div className="w-full max-w-md flex flex-col items-center">
        <div className="w-14 h-14 rounded-2xl bg-stone-100 border border-stone-200 flex items-center justify-center mb-6">
          <img src={logoIcon} alt="" className="w-8 h-8" aria-hidden="true" />
        </div>

        <h1 className="font-display text-3xl font-semibold text-stone-900 tracking-tight text-center">
          {title}
        </h1>

        <p className="mt-2 text-stone-500 text-center max-w-sm">
          {subtitle}
        </p>

        <div className="mt-8 w-full">
          {children}
        </div>
      </div>
    </div>
  )
}

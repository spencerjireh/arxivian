// Auth pages: centered card with title and subtitle around a sign-in or sign-up form.
import logoIcon from '@/assets/logo-icon.png'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: React.ReactNode
}

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#FAFAF9] px-4">
      <div className="flex w-full max-w-md flex-col items-center">
        <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl border border-stone-200 bg-stone-100">
          <img src={logoIcon} alt="" className="h-8 w-8" aria-hidden="true" />
        </div>

        <h1 className="font-display text-center text-3xl font-semibold tracking-tight text-stone-900">
          {title}
        </h1>

        <p className="mt-2 max-w-sm text-center text-stone-500">{subtitle}</p>

        <div className="mt-8 w-full">{children}</div>
      </div>
    </div>
  )
}

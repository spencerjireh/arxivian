import { Sparkles } from 'lucide-react'

interface AuthLayoutProps {
  title: string
  subtitle: string
  children: React.ReactNode
}

export default function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#FAFAF9] px-4">
      <div className="w-full max-w-md flex flex-col items-center">
        <div className="w-14 h-14 rounded-2xl bg-stone-900 flex items-center justify-center mb-6">
          <Sparkles className="w-7 h-7 text-white" strokeWidth={1.5} />
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

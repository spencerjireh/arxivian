import { Toaster as SonnerToaster } from 'sonner'

export default function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      duration={5000}
      gap={8}
      toastOptions={{
        unstyled: true,
        classNames: {
          toast:
            'flex items-start gap-3 w-[356px] rounded-lg px-4 py-3 shadow-md border',
          title: 'font-display text-sm font-semibold',
          description: 'text-xs mt-0.5 leading-relaxed',
          error:
            'bg-[var(--color-error-soft)] text-[var(--color-error)] border-[var(--color-error)]/20',
          success:
            'bg-[var(--color-success-soft)] text-[var(--color-success)] border-[var(--color-success)]/20',
          warning:
            'bg-[var(--color-accent-soft)] text-[var(--color-accent)] border-[var(--color-accent)]/20',
          info: 'bg-[var(--color-info-soft)] text-[var(--color-info)] border-[var(--color-info)]/20',
        },
      }}
    />
  )
}

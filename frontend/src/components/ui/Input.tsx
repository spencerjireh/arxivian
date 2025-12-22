import { forwardRef } from 'react'

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...props }, ref) => {
    const baseClasses = [
      'block w-full rounded-lg',
      'border border-stone-200',
      'bg-white text-stone-900',
      'shadow-sm',
      'focus:border-stone-400 focus:ring-1 focus:ring-stone-400',
      'placeholder:text-stone-400',
      'sm:text-sm',
      'transition-colors duration-150',
    ].join(' ')

    const errorClasses = error
      ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
      : ''

    const classes = `${baseClasses} ${errorClasses} ${className}`

    return (
      <div>
        {label && (
          <label className="block text-sm font-medium text-stone-700 mb-1.5">
            {label}
          </label>
        )}
        <input ref={ref} className={classes} {...props} />
        {error && <p className="mt-1.5 text-sm text-red-600">{error}</p>}
      </div>
    )
  }
)

Input.displayName = 'Input'

export default Input

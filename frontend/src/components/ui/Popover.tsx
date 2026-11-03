// UI primitive: a trigger button with an anchored dialog panel. Escape and an outside
// pointerdown close it; focus moves into the panel on open and back to the trigger on close.
import { useEffect, useId, useRef, useState } from 'react'
import clsx from 'clsx'
import Button from './Button'

type TriggerProps = Pick<
  React.ComponentProps<typeof Button>,
  'variant' | 'size' | 'leftIcon' | 'className'
>

interface PopoverProps {
  /** Rendered inside the trigger button (text, icon, badge). */
  trigger: React.ReactNode
  /** Accessible name of the panel. */
  label: string
  /** The panel body; a function form receives close() for "Done"-style actions. */
  children: React.ReactNode | ((close: () => void) => React.ReactNode)
  triggerProps?: TriggerProps
  panelClassName?: string
}

const FOCUSABLE = 'input, button, select, textarea, a[href], [tabindex]:not([tabindex="-1"])'

/**
 * On phones the panel spans its nearest positioned ancestor (the root is static below
 * `sm`), so a toolbar that holds a Popover should be `relative`; from `sm` up the root
 * itself is the anchor and the panel hangs off its right edge.
 */
export default function Popover({
  trigger,
  label,
  children,
  triggerProps,
  panelClassName,
}: PopoverProps) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  // Focus goes back to the trigger when the panel closes, except after a pointerdown
  // elsewhere: the reader chose that spot, so the browser's own focus move stands.
  const restoreFocus = useRef(true)
  const panelId = useId()

  useEffect(() => {
    if (!open) return
    restoreFocus.current = true
    const button = buttonRef.current
    const panel = panelRef.current
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE)
    ;(first ?? panel)?.focus()

    const onPointerDown = (e: PointerEvent) => {
      if (rootRef.current?.contains(e.target as Node)) return
      restoreFocus.current = false
      setOpen(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
      if (restoreFocus.current) button?.focus()
    }
  }, [open])

  const close = () => setOpen(false)

  return (
    <div ref={rootRef} className="sm:relative">
      <Button
        ref={buttonRef}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        onClick={() => setOpen((value) => !value)}
        {...triggerProps}
      >
        {trigger}
      </Button>
      {open && (
        <div
          ref={panelRef}
          id={panelId}
          role="dialog"
          aria-label={label}
          tabIndex={-1}
          className={clsx(
            'absolute inset-x-0 top-full z-50 mt-2 rounded-xl border border-stone-200 bg-white p-4 shadow-lg',
            'sm:inset-x-auto sm:right-0 sm:w-80',
            panelClassName
          )}
        >
          {typeof children === 'function' ? children(close) : children}
        </div>
      )}
    </div>
  )
}

import { useEffect, useRef, useState } from 'react'

interface UseInViewOptions {
  once?: boolean
  margin?: string
}

export function useInView<T extends HTMLElement = HTMLDivElement>(
  options: UseInViewOptions = {}
): [React.RefObject<T | null>, boolean] {
  const { once = true, margin = '0px' } = options
  const ref = useRef<T | null>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || typeof IntersectionObserver === 'undefined') return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          if (once) observer.disconnect()
        } else if (!once) {
          setInView(false)
        }
      },
      { rootMargin: margin }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [once, margin])

  return [ref, inView]
}

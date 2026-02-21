/* eslint-disable react-refresh/only-export-components */
// Lightweight mock for framer-motion that renders plain HTML elements

import { forwardRef } from 'react'
import type { ReactNode, ElementType, ComponentPropsWithRef } from 'react'

const animationProps = new Set([
  'initial', 'animate', 'exit', 'variants', 'transition',
  'whileHover', 'whileTap', 'whileInView', 'whileFocus', 'whileDrag',
  'layout', 'layoutId', 'onAnimationStart', 'onAnimationComplete',
  'viewport', 'drag', 'dragConstraints', 'dragElastic',
])

function filterProps(props: Record<string, unknown>): Record<string, unknown> {
  const filtered: Record<string, unknown> = {}
  for (const key of Object.keys(props)) {
    if (!animationProps.has(key)) {
      filtered[key] = props[key]
    }
  }
  return filtered
}

function createMotionComponent(tag: ElementType) {
  return forwardRef<unknown, ComponentPropsWithRef<typeof tag> & Record<string, unknown>>(
    function MotionProxy(props, ref) {
      const Tag = tag as ElementType
      return <Tag ref={ref} {...filterProps(props)} />
    }
  )
}

const componentCache = new Map<string, ReturnType<typeof createMotionComponent>>()

export const motion = new Proxy({} as Record<string, ReturnType<typeof createMotionComponent>>, {
  get(_target, prop: string) {
    let component = componentCache.get(prop)
    if (!component) {
      component = createMotionComponent(prop as ElementType)
      componentCache.set(prop, component)
    }
    return component
  },
})

export function AnimatePresence({ children }: { children?: ReactNode }) {
  return <>{children}</>
}

export function useReducedMotion() {
  return false
}

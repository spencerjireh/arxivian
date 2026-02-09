import { useEffect, useRef, useCallback } from 'react'
import { useReducedMotion } from 'framer-motion'

// -- Internal types --

interface EquationNode {
  x: number
  y: number
  vx: number
  vy: number
  opacity: number
  fontSize: number
  rotation: number
  depth: number
  wobblePhase: number
  wobbleAmplitude: number
  glowRadius: number
  textWidth: number
  text: string
  displayX: number
  displayY: number
}

interface SmoothedMouse {
  x: number
  y: number
  targetX: number
  targetY: number
  active: boolean
}

// -- Equation corpus --

const EQUATIONS = [
  // Original 14
  'P(A|B) = P(B|A)P(A) / P(B)',
  'softmax(QK^T / sqrt(d_k))',
  'nabla x B = mu_0 J',
  'det(A - lambda I) = 0',
  'H = -J sum s_i s_j',
  'F_uv = d_u A_v - d_v A_u',
  'int_dOmega omega = int_Omega d omega',
  'L = -1/4 F_uv F^uv',
  'sum f^(n)(a)/n! (x-a)^n',
  'attention(Q, K, V)',
  'TransformerBlock',
  'arXiv:2301.07041',
  'arXiv:1706.03762',
  'arXiv:2310.06825',
  // Additional
  'e^(i*pi) + 1 = 0',
  'E = mc^2',
  'i*h*d/dt|psi> = H|psi>',
  'H(X) = -sum p(x) log p(x)',
  'theta -= alpha * grad J(theta)',
  'L = -sum y*log(y_hat)',
  'sigma(z) = 1/(1+e^(-z))',
  'KL(P || Q) = sum P log(P/Q)',
  "d/dx[f(g(x))] = f'(g(x))g'(x)",
  'arXiv:2005.14165',
  'arXiv:2303.08774',
]

const NODE_COUNT = 25
const EDGE_MARGIN = 40
const LINE_THRESHOLD = 180
const GLOW_RADIUS = 200
const MOUSE_LERP = 0.08

function isArxivId(text: string): boolean {
  return text.startsWith('arXiv:')
}

function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function createNodes(width: number, height: number): EquationNode[] {
  const shuffled = [...EQUATIONS].sort(() => Math.random() - 0.5)
  return Array.from({ length: NODE_COUNT }, (_, i) => {
    const text = shuffled[i % shuffled.length]
    const isId = isArxivId(text)
    return {
      x: randomRange(EDGE_MARGIN, width - EDGE_MARGIN),
      y: randomRange(EDGE_MARGIN, height - EDGE_MARGIN),
      vx: randomRange(-0.3, 0.3) || 0.1,
      vy: randomRange(-0.3, 0.3) || 0.1,
      opacity: randomRange(0.08, 0.18),
      fontSize: isId ? randomRange(11, 14) : randomRange(11, 28),
      rotation: randomRange(-5, 5),
      depth: randomRange(0.2, 1.0),
      wobblePhase: randomRange(0, Math.PI * 2),
      wobbleAmplitude: randomRange(0.3, 0.8),
      glowRadius: 0,
      textWidth: 0,
      text,
      displayX: 0,
      displayY: 0,
    }
  })
}

interface Props {
  className?: string
}

export default function EquationConstellation({ className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const nodesRef = useRef<EquationNode[]>([])
  const mouseRef = useRef<SmoothedMouse>({
    x: 0,
    y: 0,
    targetX: 0,
    targetY: 0,
    active: false,
  })
  const rafRef = useRef<number>(0)
  const lastTimeRef = useRef<number>(0)
  const reducedMotion = useReducedMotion()

  const setupCanvas = useCallback(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const rect = container.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    canvas.width = rect.width * dpr
    canvas.height = rect.height * dpr
    canvas.style.width = `${rect.width}px`
    canvas.style.height = `${rect.height}px`

    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.scale(dpr, dpr)
    }

    return { width: rect.width, height: rect.height }
  }, [])

  const measureTextWidths = useCallback((ctx: CanvasRenderingContext2D, nodes: EquationNode[]) => {
    for (const node of nodes) {
      ctx.font = `${node.fontSize}px 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace`
      node.textWidth = ctx.measureText(node.text).width
    }
  }, [])

  const drawStaticFrame = useCallback((width: number, height: number) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.clearRect(0, 0, width, height)

    const nodes = nodesRef.current

    // Draw lines
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x
        const dy = nodes[i].y - nodes[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < LINE_THRESHOLD) {
          const lineOpacity = 0.03 + 0.03 * (1 - dist / LINE_THRESHOLD)
          ctx.beginPath()
          ctx.moveTo(nodes[i].x, nodes[i].y)
          ctx.lineTo(nodes[j].x, nodes[j].y)
          ctx.strokeStyle = `rgba(168, 162, 158, ${lineOpacity})`
          ctx.lineWidth = 0.5 + 0.5 * (1 - dist / LINE_THRESHOLD)
          ctx.stroke()
        }
      }
    }

    // Draw text
    for (const node of nodes) {
      ctx.save()
      ctx.translate(node.x, node.y)
      ctx.rotate((node.rotation * Math.PI) / 180)
      ctx.font = `${node.fontSize}px 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace`
      ctx.fillStyle = `rgba(120, 113, 108, ${node.opacity})`
      ctx.fillText(node.text, -node.textWidth / 2, node.fontSize / 3)
      ctx.restore()
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    let resizeTimer: ReturnType<typeof setTimeout>

    const init = async () => {
      await document.fonts.ready

      const dims = setupCanvas()
      if (!dims) return

      nodesRef.current = createNodes(dims.width, dims.height)

      const ctx = canvas.getContext('2d')
      if (!ctx) return
      measureTextWidths(ctx, nodesRef.current)

      if (reducedMotion) {
        drawStaticFrame(dims.width, dims.height)
        return
      }

      // Animation loop
      const animate = (time: number) => {
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        const dpr = window.devicePixelRatio || 1
        const w = canvas.width / dpr
        const h = canvas.height / dpr

        // Delta time normalization targeting 60fps
        const rawDelta = lastTimeRef.current ? (time - lastTimeRef.current) / (1000 / 60) : 1
        const dt = Math.min(rawDelta, 3)
        lastTimeRef.current = time

        // Lerp smoothed mouse
        const mouse = mouseRef.current
        if (mouse.active) {
          mouse.x += (mouse.targetX - mouse.x) * MOUSE_LERP
          mouse.y += (mouse.targetY - mouse.y) * MOUSE_LERP
        }

        ctx.clearRect(0, 0, w, h)

        const nodes = nodesRef.current

        // Update nodes
        for (const node of nodes) {
          // Drift
          node.x += node.vx * dt
          node.y += node.vy * dt

          // Sinusoidal wobble
          node.wobblePhase += 0.01 * dt
          node.x += Math.sin(node.wobblePhase) * node.wobbleAmplitude * 0.1 * dt
          node.y += Math.cos(node.wobblePhase * 0.7) * node.wobbleAmplitude * 0.1 * dt

          // Soft edge bounce
          if (node.x < EDGE_MARGIN) {
            node.vx = Math.abs(node.vx)
          } else if (node.x > w - EDGE_MARGIN) {
            node.vx = -Math.abs(node.vx)
          }
          if (node.y < EDGE_MARGIN) {
            node.vy = Math.abs(node.vy)
          } else if (node.y > h - EDGE_MARGIN) {
            node.vy = -Math.abs(node.vy)
          }

          // Mouse parallax
          let parallaxX = 0
          let parallaxY = 0
          if (mouse.active) {
            const centerX = w / 2
            const centerY = h / 2
            parallaxX = (mouse.x - centerX) * node.depth * 0.02
            parallaxY = (mouse.y - centerY) * node.depth * 0.02
          }
          node.displayX = node.x + parallaxX
          node.displayY = node.y + parallaxY

          // Proximity glow
          node.glowRadius = 0
          if (mouse.active) {
            const dx = node.displayX - mouse.x
            const dy = node.displayY - mouse.y
            const dist = Math.sqrt(dx * dx + dy * dy)
            if (dist < GLOW_RADIUS) {
              node.glowRadius = 0.15 * (1 - dist / GLOW_RADIUS)
            }
          }
        }

        // Draw constellation lines
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            const dx = nodes[i].displayX - nodes[j].displayX
            const dy = nodes[i].displayY - nodes[j].displayY
            const dist = Math.sqrt(dx * dx + dy * dy)
            if (dist < LINE_THRESHOLD) {
              const t = 1 - dist / LINE_THRESHOLD
              const lineOpacity = 0.03 + 0.03 * t
              ctx.beginPath()
              ctx.moveTo(nodes[i].displayX, nodes[i].displayY)
              ctx.lineTo(nodes[j].displayX, nodes[j].displayY)
              ctx.strokeStyle = `rgba(168, 162, 158, ${lineOpacity})`
              ctx.lineWidth = 0.5 + 0.5 * t
              ctx.stroke()
            }
          }
        }

        // Draw equation text
        for (const node of nodes) {
          const totalOpacity = Math.min(node.opacity + node.glowRadius, 0.35)

          ctx.save()
          ctx.translate(node.displayX, node.displayY)
          ctx.rotate((node.rotation * Math.PI) / 180)
          ctx.font = `${node.fontSize}px 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace`

          // Shadow glow
          if (node.glowRadius > 0) {
            ctx.shadowColor = `rgba(120, 113, 108, ${node.glowRadius})`
            ctx.shadowBlur = 2 + node.glowRadius * 8
          }

          ctx.fillStyle = `rgba(120, 113, 108, ${totalOpacity})`
          ctx.fillText(node.text, -node.textWidth / 2, node.fontSize / 3)
          ctx.restore()
        }

        rafRef.current = requestAnimationFrame(animate)
      }

      rafRef.current = requestAnimationFrame(animate)
    }

    init()

    // Mouse events
    const handleMouseMove = (e: MouseEvent) => {
      if (reducedMotion) return
      const rect = canvas.getBoundingClientRect()
      mouseRef.current.targetX = e.clientX - rect.left
      mouseRef.current.targetY = e.clientY - rect.top
      mouseRef.current.active = true
    }

    const handleMouseLeave = () => {
      mouseRef.current.active = false
    }

    if (!reducedMotion) {
      canvas.addEventListener('mousemove', handleMouseMove)
      canvas.addEventListener('mouseleave', handleMouseLeave)
    }

    // Resize observer
    const observer = new ResizeObserver(() => {
      clearTimeout(resizeTimer)
      resizeTimer = setTimeout(() => {
        const dims = setupCanvas()
        if (!dims) return

        // Reposition nodes that are out of bounds
        for (const node of nodesRef.current) {
          node.x = Math.min(Math.max(node.x, EDGE_MARGIN), dims.width - EDGE_MARGIN)
          node.y = Math.min(Math.max(node.y, EDGE_MARGIN), dims.height - EDGE_MARGIN)
        }

        const ctx = canvas.getContext('2d')
        if (ctx) {
          measureTextWidths(ctx, nodesRef.current)
        }

        if (reducedMotion) {
          drawStaticFrame(dims.width, dims.height)
        }
      }, 200)
    })
    observer.observe(container)

    return () => {
      cancelAnimationFrame(rafRef.current)
      observer.disconnect()
      canvas.removeEventListener('mousemove', handleMouseMove)
      canvas.removeEventListener('mouseleave', handleMouseLeave)
      clearTimeout(resizeTimer)
    }
  }, [reducedMotion, setupCanvas, measureTextWidths, drawStaticFrame])

  return (
    <div
      ref={containerRef}
      className={className}
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%', pointerEvents: 'auto' }}
      />
    </div>
  )
}

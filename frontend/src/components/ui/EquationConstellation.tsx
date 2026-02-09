import { useEffect, useRef, useCallback } from 'react'
import { useReducedMotion } from 'framer-motion'

// -- Internal types --

type DepthLayer = 'bg' | 'mid' | 'fg'

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
  layer: DepthLayer
  rotationSpeed: number
  fadeInDuration: number
  visibleDuration: number
  fadeOutDuration: number
  age: number
  lifecycleOpacity: number
}

interface SmoothedMouse {
  x: number
  y: number
  targetX: number
  targetY: number
  active: boolean
}

// -- Layer presets --

const LAYER_CONFIG = {
  bg: {
    fontSize: [30, 50],
    opacity: [0.05, 0.10],
    velocity: [-0.03, 0.03],
    parallaxMultiplier: 0.004,
  },
  mid: {
    fontSize: [18, 34],
    opacity: [0.10, 0.18],
    velocity: [-0.06, 0.06],
    parallaxMultiplier: 0.008,
  },
  fg: {
    fontSize: [14, 22],
    opacity: [0.15, 0.24],
    velocity: [-0.10, 0.10],
    parallaxMultiplier: 0.014,
  },
} as const

// Assign layers: 8 bg, 9 mid, 8 fg
const LAYER_ASSIGNMENTS: DepthLayer[] = [
  ...Array(8).fill('bg' as DepthLayer),
  ...Array(9).fill('mid' as DepthLayer),
  ...Array(8).fill('fg' as DepthLayer),
]

// -- Equation corpus (Unicode math symbols) --

const EQUATIONS = [
  // Original 14
  'P(A|B) = P(B|A)P(A) / P(B)',
  'softmax(QK\u1d40/\u221ad\u2096)',
  '\u2207 \u00d7 B = \u03bc\u2080J',
  'det(A \u2212 \u03bbI) = 0',
  'H = \u2212J\u03a3 s\u1d62s\u2c7c',
  'F_{\u03bcv} = \u2202_\u03bcA_v \u2212 \u2202_vA_\u03bc',
  '\u222b_{\u2202\u03a9} \u03c9 = \u222b_\u03a9 d\u03c9',
  '\u2112 = \u2212\u00bcF_{\u03bcv}F^{\u03bcv}',
  '\u03a3 f\u207d\u207f\u207e(a)/n! (x\u2212a)\u207f',
  'attention(Q, K, V)',
  'TransformerBlock',
  'arXiv:2301.07041',
  'arXiv:1706.03762',
  'arXiv:2310.06825',
  // Additional
  'e^{i\u03c0} + 1 = 0',
  'E = mc\u00b2',
  'i\u0127 \u2202/\u2202t|\u03c8\u27e9 = H|\u03c8\u27e9',
  'H(X) = \u2212\u03a3 p(x) log p(x)',
  '\u03b8 \u2212= \u03b1\u2207J(\u03b8)',
  '\u2112 = \u2212\u03a3 y log \u0177',
  '\u03c3(z) = 1/(1+e\u207b\u1dbb)',
  'D_{KL}(P \u2016 Q) = \u03a3 P log(P/Q)',
  'd/dx[f(g(x))] = f\u2032(g(x))g\u2032(x)',
  'arXiv:2005.14165',
  'arXiv:2303.08774',
]

const NODE_COUNT = 25
const EDGE_MARGIN = 40
const LINE_THRESHOLD = 140
const GLOW_RADIUS = 200
const MOUSE_LERP = 0.08

// Exclusion zone (fraction of canvas dimensions)
const EXCLUSION = { x1: 0.15, x2: 0.85, y1: 0.10, y2: 0.75 }

const FONT_STACK = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"

function isArxivId(text: string): boolean {
  return text.startsWith('arXiv:')
}

function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

function isInsideExclusion(x: number, y: number, w: number, h: number): boolean {
  return x > w * EXCLUSION.x1 && x < w * EXCLUSION.x2 &&
         y > h * EXCLUSION.y1 && y < h * EXCLUSION.y2
}

function randomPosition(w: number, h: number): { x: number; y: number } {
  let x: number, y: number
  let attempts = 0
  do {
    x = randomRange(EDGE_MARGIN, w - EDGE_MARGIN)
    y = randomRange(EDGE_MARGIN, h - EDGE_MARGIN)
    attempts++
  } while (isInsideExclusion(x, y, w, h) && attempts < 100)
  return { x, y }
}

function assignNodeProperties(node: EquationNode, layer: DepthLayer, text: string): void {
  const config = LAYER_CONFIG[layer]
  const isId = isArxivId(text)

  node.text = text
  node.layer = layer
  node.depth = layer === 'bg' ? randomRange(0.2, 0.33)
    : layer === 'mid' ? randomRange(0.33, 0.66)
    : randomRange(0.66, 1.0)

  node.fontSize = isId ? randomRange(14, 18) : randomRange(config.fontSize[0], config.fontSize[1])
  node.opacity = randomRange(config.opacity[0], config.opacity[1])
  node.vx = randomRange(config.velocity[0], config.velocity[1]) || 0.04
  node.vy = randomRange(config.velocity[0], config.velocity[1]) || 0.04

  node.rotation = randomRange(-5, 5)
  node.rotationSpeed = randomRange(-0.015, 0.015)
  node.wobblePhase = randomRange(0, Math.PI * 2)
  node.wobbleAmplitude = randomRange(0.1, 0.25)

  node.fadeInDuration = randomRange(1500, 3000)
  node.visibleDuration = randomRange(8000, 18000)
  node.fadeOutDuration = randomRange(1500, 3000)
  node.lifecycleOpacity = 0

  node.glowRadius = 0
  node.textWidth = 0
}

function respawnNode(node: EquationNode, w: number, h: number): void {
  const pos = randomPosition(w, h)
  node.x = pos.x
  node.y = pos.y

  const shuffled = EQUATIONS.filter(e => {
    // ArXiv IDs only on mid/fg
    if (isArxivId(e) && node.layer === 'bg') return false
    return true
  })
  const text = shuffled[Math.floor(Math.random() * shuffled.length)]

  assignNodeProperties(node, node.layer, text)
  node.age = 0
}

function areAdjacentLayers(a: DepthLayer, b: DepthLayer): boolean {
  if (a === b) return true
  if (a === 'bg' && b === 'mid') return true
  if (a === 'mid' && b === 'bg') return true
  if (a === 'mid' && b === 'fg') return true
  if (a === 'fg' && b === 'mid') return true
  return false
}

function createNodes(width: number, height: number): EquationNode[] {
  const shuffled = [...EQUATIONS].sort(() => Math.random() - 0.5)
  const shuffledLayers = [...LAYER_ASSIGNMENTS].sort(() => Math.random() - 0.5)

  return Array.from({ length: NODE_COUNT }, (_, i) => {
    let layer = shuffledLayers[i]
    const text = shuffled[i % shuffled.length]

    // ArXiv IDs only on mid/fg
    if (isArxivId(text) && layer === 'bg') {
      layer = Math.random() < 0.5 ? 'mid' : 'fg'
    }

    const config = LAYER_CONFIG[layer]
    const isId = isArxivId(text)
    const pos = randomPosition(width, height)

    const depth = layer === 'bg' ? randomRange(0.2, 0.33)
      : layer === 'mid' ? randomRange(0.33, 0.66)
      : randomRange(0.66, 1.0)

    const totalLifetime = randomRange(1500, 3000) + randomRange(8000, 18000) + randomRange(1500, 3000)

    const node: EquationNode = {
      x: pos.x,
      y: pos.y,
      vx: randomRange(config.velocity[0], config.velocity[1]) || 0.04,
      vy: randomRange(config.velocity[0], config.velocity[1]) || 0.04,
      opacity: randomRange(config.opacity[0], config.opacity[1]),
      fontSize: isId ? randomRange(14, 18) : randomRange(config.fontSize[0], config.fontSize[1]),
      rotation: randomRange(-5, 5),
      depth,
      wobblePhase: randomRange(0, Math.PI * 2),
      wobbleAmplitude: randomRange(0.1, 0.25),
      glowRadius: 0,
      textWidth: 0,
      text,
      displayX: 0,
      displayY: 0,
      layer,
      rotationSpeed: randomRange(-0.015, 0.015),
      fadeInDuration: randomRange(1500, 3000),
      visibleDuration: randomRange(8000, 18000),
      fadeOutDuration: randomRange(1500, 3000),
      age: randomRange(0, totalLifetime),
      lifecycleOpacity: 1.0,
    }
    return node
  })
}

interface Props {
  className?: string
}

export default function EquationConstellation({ className }: Props) {
  const bgCanvasRef = useRef<HTMLCanvasElement>(null)
  const midCanvasRef = useRef<HTMLCanvasElement>(null)
  const fgCanvasRef = useRef<HTMLCanvasElement>(null)
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
    const container = containerRef.current
    if (!container) return

    const canvases = [bgCanvasRef.current, midCanvasRef.current, fgCanvasRef.current]
    if (canvases.some(c => !c)) return

    const rect = container.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1

    for (const canvas of canvases) {
      if (!canvas) continue
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      canvas.style.width = `${rect.width}px`
      canvas.style.height = `${rect.height}px`

      const ctx = canvas.getContext('2d')
      if (ctx) {
        ctx.scale(dpr, dpr)
      }
    }

    return { width: rect.width, height: rect.height }
  }, [])

  const measureTextWidths = useCallback((ctx: CanvasRenderingContext2D, nodes: EquationNode[]) => {
    for (const node of nodes) {
      ctx.font = `italic ${node.fontSize}px ${FONT_STACK}`
      node.textWidth = ctx.measureText(node.text).width
    }
  }, [])

  const drawStaticFrame = useCallback((width: number, height: number) => {
    const bgCtx = bgCanvasRef.current?.getContext('2d')
    const midCtx = midCanvasRef.current?.getContext('2d')
    const fgCtx = fgCanvasRef.current?.getContext('2d')
    if (!bgCtx || !midCtx || !fgCtx) return

    const layerCtx: Record<DepthLayer, CanvasRenderingContext2D> = {
      bg: bgCtx, mid: midCtx, fg: fgCtx,
    }

    bgCtx.clearRect(0, 0, width, height)
    midCtx.clearRect(0, 0, width, height)
    fgCtx.clearRect(0, 0, width, height)

    const nodes = nodesRef.current

    // Draw lines on fg canvas (no blur needed for thin lines)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (!areAdjacentLayers(nodes[i].layer, nodes[j].layer)) continue
        const dx = nodes[i].x - nodes[j].x
        const dy = nodes[i].y - nodes[j].y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < LINE_THRESHOLD) {
          const t = 1 - dist / LINE_THRESHOLD
          const lineOpacity = 0.02 + 0.03 * t
          fgCtx.beginPath()
          fgCtx.moveTo(nodes[i].x, nodes[i].y)
          fgCtx.lineTo(nodes[j].x, nodes[j].y)
          fgCtx.strokeStyle = `rgba(168, 162, 158, ${lineOpacity})`
          fgCtx.lineWidth = 0.3 + 0.4 * t
          fgCtx.stroke()
        }
      }
    }

    // Draw text to layer-appropriate canvas (CSS handles blur)
    for (const node of nodes) {
      const ctx = layerCtx[node.layer]
      ctx.save()
      ctx.translate(node.x, node.y)
      ctx.rotate((node.rotation * Math.PI) / 180)
      ctx.font = `italic ${node.fontSize}px ${FONT_STACK}`
      ctx.fillStyle = `rgba(120, 113, 108, ${node.opacity})`
      ctx.fillText(node.text, -node.textWidth / 2, node.fontSize / 3)
      ctx.restore()
    }
  }, [])

  useEffect(() => {
    const fgCanvas = fgCanvasRef.current
    const container = containerRef.current
    if (!fgCanvas || !bgCanvasRef.current || !midCanvasRef.current || !container) return

    let resizeTimer: ReturnType<typeof setTimeout>

    const init = async () => {
      await document.fonts.ready

      const dims = setupCanvas()
      if (!dims) return

      nodesRef.current = createNodes(dims.width, dims.height)

      const ctx = fgCanvas.getContext('2d')
      if (!ctx) return
      measureTextWidths(ctx, nodesRef.current)

      if (reducedMotion) {
        drawStaticFrame(dims.width, dims.height)
        return
      }

      // Animation loop
      const animate = (time: number) => {
        const bgCtx = bgCanvasRef.current?.getContext('2d')
        const midCtx = midCanvasRef.current?.getContext('2d')
        const fgCtx = fgCanvasRef.current?.getContext('2d')
        if (!bgCtx || !midCtx || !fgCtx) return

        const layerCtx: Record<DepthLayer, CanvasRenderingContext2D> = {
          bg: bgCtx, mid: midCtx, fg: fgCtx,
        }

        const dpr = window.devicePixelRatio || 1
        const w = fgCanvasRef.current!.width / dpr
        const h = fgCanvasRef.current!.height / dpr

        // Delta time
        const realDeltaMs = lastTimeRef.current ? (time - lastTimeRef.current) : 16.67
        const rawDelta = realDeltaMs / (1000 / 60)
        const dt = Math.min(rawDelta, 3)
        lastTimeRef.current = time

        // Lerp smoothed mouse
        const mouse = mouseRef.current
        if (mouse.active) {
          mouse.x += (mouse.targetX - mouse.x) * MOUSE_LERP
          mouse.y += (mouse.targetY - mouse.y) * MOUSE_LERP
        }

        // Clear all 3 canvases
        bgCtx.clearRect(0, 0, w, h)
        midCtx.clearRect(0, 0, w, h)
        fgCtx.clearRect(0, 0, w, h)

        const nodes = nodesRef.current

        // Exclusion zone boundaries in pixels
        const exLeft = w * EXCLUSION.x1
        const exRight = w * EXCLUSION.x2
        const exTop = h * EXCLUSION.y1
        const exBottom = h * EXCLUSION.y2

        // Update nodes
        for (const node of nodes) {
          // Lifecycle age tracking
          node.age += realDeltaMs
          const totalLifetime = node.fadeInDuration + node.visibleDuration + node.fadeOutDuration

          if (node.age < node.fadeInDuration) {
            node.lifecycleOpacity = node.age / node.fadeInDuration
          } else if (node.age < node.fadeInDuration + node.visibleDuration) {
            node.lifecycleOpacity = 1.0
          } else if (node.age < totalLifetime) {
            node.lifecycleOpacity = 1.0 - (node.age - node.fadeInDuration - node.visibleDuration) / node.fadeOutDuration
          } else {
            // Respawn
            respawnNode(node, w, h)
            // Re-measure text width using the layer's context
            const ctx = layerCtx[node.layer]
            ctx.font = `italic ${node.fontSize}px ${FONT_STACK}`
            node.textWidth = ctx.measureText(node.text).width
          }

          // Drift
          node.x += node.vx * dt
          node.y += node.vy * dt

          // Rotation drift
          node.rotation += node.rotationSpeed * dt

          // Sinusoidal wobble
          node.wobblePhase += 0.005 * dt
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

          // Center exclusion zone: gently steer away
          if (isInsideExclusion(node.x, node.y, w, h)) {
            const distToLeft = node.x - exLeft
            const distToRight = exRight - node.x
            const distToTop = node.y - exTop
            const distToBottom = exBottom - node.y

            const minHoriz = Math.min(distToLeft, distToRight)
            const minVert = Math.min(distToTop, distToBottom)

            if (minHoriz < minVert) {
              node.vx = distToLeft < distToRight ? -Math.abs(node.vx || 0.04) : Math.abs(node.vx || 0.04)
            } else {
              node.vy = distToTop < distToBottom ? -Math.abs(node.vy || 0.04) : Math.abs(node.vy || 0.04)
            }
          }

          // Mouse parallax (layer-based multiplier)
          const parallaxFactor = LAYER_CONFIG[node.layer].parallaxMultiplier
          let parallaxX = 0
          let parallaxY = 0
          if (mouse.active) {
            const centerX = w / 2
            const centerY = h / 2
            parallaxX = (mouse.x - centerX) * node.depth * parallaxFactor
            parallaxY = (mouse.y - centerY) * node.depth * parallaxFactor
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

        // Draw constellation lines on fg canvas (no blur needed for thin lines)
        for (let i = 0; i < nodes.length; i++) {
          for (let j = i + 1; j < nodes.length; j++) {
            if (!areAdjacentLayers(nodes[i].layer, nodes[j].layer)) continue
            const dx = nodes[i].displayX - nodes[j].displayX
            const dy = nodes[i].displayY - nodes[j].displayY
            const dist = Math.sqrt(dx * dx + dy * dy)
            if (dist < LINE_THRESHOLD) {
              const t = 1 - dist / LINE_THRESHOLD
              // Factor in lifecycleOpacity of both nodes
              const pairOpacity = Math.min(nodes[i].lifecycleOpacity, nodes[j].lifecycleOpacity)
              const lineOpacity = (0.02 + 0.03 * t) * pairOpacity
              if (lineOpacity < 0.001) continue
              fgCtx.beginPath()
              fgCtx.moveTo(nodes[i].displayX, nodes[i].displayY)
              fgCtx.lineTo(nodes[j].displayX, nodes[j].displayY)
              fgCtx.strokeStyle = `rgba(168, 162, 158, ${lineOpacity})`
              fgCtx.lineWidth = 0.3 + 0.4 * t
              fgCtx.stroke()
            }
          }
        }

        // Draw equation text to layer-appropriate canvas (CSS handles blur)
        for (const node of nodes) {
          // Skip fully faded out nodes
          if (node.lifecycleOpacity < 0.01) continue

          const totalOpacity = Math.min(
            (node.opacity * node.lifecycleOpacity) + node.glowRadius,
            0.35,
          )
          if (totalOpacity < 0.005) continue

          const ctx = layerCtx[node.layer]
          ctx.save()

          ctx.translate(node.displayX, node.displayY)
          ctx.rotate((node.rotation * Math.PI) / 180)
          ctx.font = `italic ${node.fontSize}px ${FONT_STACK}`

          // Shadow glow
          if (node.glowRadius > 0) {
            ctx.shadowColor = `rgba(120, 113, 108, ${node.glowRadius * node.lifecycleOpacity})`
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

    // Mouse events on fg canvas (topmost, has pointerEvents: auto)
    const handleMouseMove = (e: MouseEvent) => {
      if (reducedMotion) return
      const rect = fgCanvas.getBoundingClientRect()
      mouseRef.current.targetX = e.clientX - rect.left
      mouseRef.current.targetY = e.clientY - rect.top
      mouseRef.current.active = true
    }

    const handleMouseLeave = () => {
      mouseRef.current.active = false
    }

    if (!reducedMotion) {
      fgCanvas.addEventListener('mousemove', handleMouseMove)
      fgCanvas.addEventListener('mouseleave', handleMouseLeave)
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

        const ctx = fgCanvas.getContext('2d')
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
      fgCanvas.removeEventListener('mousemove', handleMouseMove)
      fgCanvas.removeEventListener('mouseleave', handleMouseLeave)
      clearTimeout(resizeTimer)
    }
  }, [reducedMotion, setupCanvas, measureTextWidths, drawStaticFrame])

  const canvasBase: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    display: 'block',
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
  }

  return (
    <div
      ref={containerRef}
      className={className}
      aria-hidden="true"
      style={{ position: 'absolute', inset: 0, zIndex: 0, pointerEvents: 'none' }}
    >
      <canvas
        ref={bgCanvasRef}
        style={{ ...canvasBase, filter: 'blur(2.5px)' }}
      />
      <canvas
        ref={midCanvasRef}
        style={{ ...canvasBase, filter: 'blur(1.1px)' }}
      />
      <canvas
        ref={fgCanvasRef}
        style={{ ...canvasBase, pointerEvents: 'auto' }}
      />
    </div>
  )
}

// Landing hero: static decorative artwork behind the headline.
import clsx from 'clsx'

const GLYPHS = [
  { x: 8, y: 18, text: '∇ × B = μ₀J', size: 15, opacity: 0.16 },
  { x: 74, y: 12, text: 'θ −= α∇J(θ)', size: 14, opacity: 0.2 },
  { x: 82, y: 42, text: 'ℒ = −Σ y log ŷ', size: 13, opacity: 0.14 },
  { x: 12, y: 58, text: 'softmax(QKᵀ/√d)V', size: 14, opacity: 0.18 },
  { x: 62, y: 74, text: 'σ(z) = 1/(1+e⁻ᶻ)', size: 13, opacity: 0.14 },
  { x: 28, y: 84, text: '∫_{∂Ω} ω = ∫_Ω dω', size: 12, opacity: 0.12 },
  { x: 46, y: 30, text: 'p(x) = Π p(xᵢ | x<ᵢ)', size: 12, opacity: 0.12 },
]

/** Static hero ornament: faint equations over a dotted grid. Decorative only. */
export default function HeroArt({ className }: { className?: string }) {
  return (
    <svg
      className={clsx('pointer-events-none absolute inset-0 h-full w-full', className)}
      aria-hidden="true"
      preserveAspectRatio="none"
      viewBox="0 0 100 100"
    >
      <defs>
        <pattern id="hero-dots" width="4" height="4" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="0.18" fill="#a8a29e" />
        </pattern>
      </defs>
      <rect width="100" height="100" fill="url(#hero-dots)" opacity="0.5" />
      {GLYPHS.map((g) => (
        <text
          key={g.text}
          x={g.x}
          y={g.y}
          fontSize={g.size / 4}
          fontFamily="ui-serif, Georgia, serif"
          fill="#57534e"
          opacity={g.opacity}
        >
          {g.text}
        </text>
      ))}
    </svg>
  )
}

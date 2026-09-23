// /about route: the marketing page (hero, features, credibility). The feed itself is at /.
import Credibility from '@/features/landing/components/Credibility'
import FeatureGrid from '@/features/landing/components/FeatureGrid'
import Hero from '@/features/landing/components/Hero'
import SectionDivider from '@/features/landing/components/SectionDivider'

export default function AboutPage() {
  return (
    <div className="paper-grain flex flex-1 flex-col">
      <Hero />
      <SectionDivider animated />
      <FeatureGrid />
      <Credibility />
    </div>
  )
}

// /about route: the marketing page (hero, features, credibility). The feed itself is at /.
import Credibility from '../components/landing/Credibility'
import FeatureGrid from '../components/landing/FeatureGrid'
import Hero from '../components/landing/Hero'
import SectionDivider from '../components/landing/SectionDivider'

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

// / route: public landing page; signed-in users are redirected to /feed.
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@clerk/clerk-react'
import Credibility from '../components/landing/Credibility'
import FeatureGrid from '../components/landing/FeatureGrid'
import Hero from '../components/landing/Hero'
import SectionDivider from '../components/landing/SectionDivider'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

export default function LandingPage() {
  const { isSignedIn } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (isSignedIn) {
      void navigate('/feed', { replace: true })
    }
  }, [isSignedIn, navigate])

  return (
    <div className="paper-grain flex min-h-screen flex-col bg-[#FAFAF9]">
      <PublicHeader />
      <Hero />
      <SectionDivider animated />
      <FeatureGrid />
      <Credibility />
      <Footer />
    </div>
  )
}

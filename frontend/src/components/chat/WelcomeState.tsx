// Welcome state shown when no conversation is active

import { useNavigate } from 'react-router-dom'
import { Sparkles, ArrowRight } from 'lucide-react'

export default function WelcomeState() {
  const navigate = useNavigate()

  const handleNewConversation = () => {
    navigate('/new')
  }

  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-lg text-center animate-fade-in">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-stone-900 flex items-center justify-center mx-auto mb-8 shadow-lg">
          <Sparkles className="w-7 h-7 text-white" strokeWidth={1.5} />
        </div>

        {/* Title */}
        <h1 className="font-display text-4xl text-stone-900 mb-4 tracking-tight">
          Welcome back
        </h1>

        {/* Subtitle */}
        <p className="text-stone-500 text-lg leading-relaxed mb-10">
          Start a new conversation to explore academic research, get answers to complex questions, or discover new insights.
        </p>

        {/* CTA Button */}
        <button
          onClick={handleNewConversation}
          className="
            inline-flex items-center gap-3 px-6 py-3.5
            bg-stone-900 hover:bg-stone-800 text-white
            rounded-xl transition-all duration-200
            text-base font-medium
            shadow-md hover:shadow-lg
            btn-hover-lift
          "
        >
          Start a new conversation
          <ArrowRight className="w-4 h-4" strokeWidth={2} />
        </button>

        {/* Decorative elements */}
        <div className="mt-16 flex items-center justify-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-stone-200" />
          <div className="w-1.5 h-1.5 rounded-full bg-stone-300" />
          <div className="w-1.5 h-1.5 rounded-full bg-stone-200" />
        </div>
      </div>
    </div>
  )
}

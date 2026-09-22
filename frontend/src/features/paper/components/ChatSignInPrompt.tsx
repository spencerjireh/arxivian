// Paper detail: the chat panel's frame for an anonymous reader, with a sign-in prompt.
import { LogIn, MessageSquare } from 'lucide-react'
import SignInLink from '@/components/ui/SignInLink'

export default function ChatSignInPrompt() {
  return (
    <section
      aria-label="Ask about this paper"
      className="flex flex-col rounded-xl border border-stone-200 bg-white lg:sticky lg:top-20"
    >
      <header className="flex items-center gap-2 border-b border-stone-100 px-4 py-3">
        <MessageSquare className="h-4 w-4 text-stone-400" strokeWidth={1.5} />
        <h2 className="font-display flex-1 truncate text-lg text-stone-900">
          Ask about this paper
        </h2>
      </header>
      <div className="space-y-3 px-4 py-6">
        <p className="text-sm text-stone-600">
          Sign in to ask questions about this paper. Answers cite only the paper&apos;s own text,
          and free accounts get ten turns a day.
        </p>
        <SignInLink variant="button" leftIcon={<LogIn className="h-4 w-4" strokeWidth={1.5} />}>
          Sign in to chat
        </SignInLink>
      </div>
    </section>
  )
}

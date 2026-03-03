import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

const CONTACT_EMAIL = 'email@spencerjireh.com'
const EFFECTIVE_DATE = 'March 2, 2026'

interface SectionProps {
  title: string
  children: React.ReactNode
}

function Section({ title, children }: SectionProps) {
  return (
    <section className="animate-fade-in">
      <h2 className="font-display text-lg font-semibold text-stone-900 mb-3">
        {title}
      </h2>
      <div className="text-sm text-stone-600 leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  )
}

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#FAFAF9] flex flex-col paper-grain">
      <PublicHeader />

      <article className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 space-y-10 flex-1">
        {/* Header */}
        <header
          style={{ '--stagger-index': 0 } as React.CSSProperties}
          className="animate-stagger"
        >
          <p className="text-sm text-stone-500 uppercase tracking-wider font-medium mb-4">
            Legal
          </p>
          <h1 className="font-display text-4xl sm:text-5xl text-stone-900 tracking-tight mb-4">
            Privacy Policy
          </h1>
          <p className="text-stone-500">
            Effective {EFFECTIVE_DATE}
          </p>
        </header>

        {/* Intro */}
        <p
          style={{ '--stagger-index': 1 } as React.CSSProperties}
          className="text-sm text-stone-600 leading-relaxed animate-stagger"
        >
          Arxivian is an AI-powered research assistant for analyzing academic papers from arXiv.
          This policy describes what data we collect, how we use it, and your rights regarding
          that data. We are committed to handling your information responsibly and transparently.
        </p>

        <Section title="1. Information We Collect">
          <p>
            <strong className="text-stone-800">Account information.</strong>{' '}
            When you sign up, we receive your name, email address, and profile picture from your
            authentication provider (Google). We do not store your password -- authentication is
            handled entirely by Clerk, our identity provider.
          </p>
          <p>
            <strong className="text-stone-800">Usage data.</strong>{' '}
            We track daily usage counters (conversations started, papers ingested) to enforce
            rate limits. We do not track browsing behavior, page views, or analytics beyond
            what is needed for the service to function.
          </p>
          <p>
            <strong className="text-stone-800">Conversations.</strong>{' '}
            Your chat messages and the AI-generated responses are stored so you can return to
            previous conversations. Paper content you ingest is chunked and embedded for
            retrieval but is not shared with other users.
          </p>
        </Section>

        <Section title="2. How We Use Your Data">
          <ul className="list-disc list-inside space-y-1.5 text-stone-600">
            <li>To provide and maintain the Arxivian service</li>
            <li>To authenticate your identity and manage your account</li>
            <li>To enforce usage limits based on your account tier</li>
            <li>To improve response quality through observability tooling (Langfuse)</li>
            <li>To respond to support requests</li>
          </ul>
          <p>
            We do not sell your personal data. We do not use your data for advertising.
          </p>
        </Section>

        <Section title="3. Third-Party Services">
          <p>Arxivian relies on the following third-party services to operate:</p>
          <ul className="list-disc list-inside space-y-1.5 text-stone-600">
            <li>
              <strong className="text-stone-800">Clerk</strong> -- authentication and user
              management. Subject to{' '}
              <a
                href="https://clerk.com/legal/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 hover:text-stone-900 transition-colors"
              >
                Clerk's Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-stone-800">OpenAI</strong> -- language model inference for
              generating responses. Your conversation messages are sent to OpenAI's API for
              processing. Subject to{' '}
              <a
                href="https://openai.com/policies/privacy-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 hover:text-stone-900 transition-colors"
              >
                OpenAI's Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-stone-800">NVIDIA NIM</strong> -- language model inference
              as an alternative provider. Conversation messages may be sent to NVIDIA's API
              depending on model selection. Subject to{' '}
              <a
                href="https://www.nvidia.com/en-us/about-nvidia/privacy-policy/"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 hover:text-stone-900 transition-colors"
              >
                NVIDIA's Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-stone-800">Jina AI</strong> -- text embedding service used
              to convert paper content into vector representations for search and retrieval.
              Paper text is sent to Jina's API for embedding. Subject to{' '}
              <a
                href="https://jina.ai/legal/#privacy-policy"
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2 hover:text-stone-900 transition-colors"
              >
                Jina AI's Privacy Policy
              </a>.
            </li>
            <li>
              <strong className="text-stone-800">Langfuse</strong> -- self-hosted LLM
              observability for monitoring response quality. Traces are stored on our own
              infrastructure.
            </li>
            <li>
              <strong className="text-stone-800">arXiv</strong> -- paper metadata and content
              retrieval. We access publicly available papers through arXiv's API.
            </li>
          </ul>
        </Section>

        <Section title="4. Google User Data Disclosure">
          <p>
            Arxivian uses Google Sign-In (via Clerk) to authenticate users. Through this
            process, we access the following data from your Google account:
          </p>
          <ul className="list-disc list-inside space-y-1.5 text-stone-600">
            <li>Your name</li>
            <li>Your email address</li>
            <li>Your profile picture</li>
          </ul>
          <p>
            This data is used solely to create and manage your Arxivian account, display your
            identity within the application, and communicate with you if necessary. We do not
            request access to any other Google services or data beyond basic profile information.
          </p>
          <p>
            Arxivian's use and transfer of information received from Google APIs adheres to
            the{' '}
            <a
              href="https://developers.google.com/terms/api-services-user-data-policy"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-stone-900 transition-colors"
            >
              Google API Services User Data Policy
            </a>, including the Limited Use requirements. Specifically:
          </p>
          <ul className="list-disc list-inside space-y-1.5 text-stone-600">
            <li>We do not sell or transfer Google user data to third parties, advertising
              platforms, data brokers, or information resellers.</li>
            <li>We do not use Google user data for serving ads, retargeting, or
              interest-based advertising.</li>
            <li>We do not use Google user data for credit assessments, lending, or
              surveillance purposes.</li>
            <li>Human access to Google user data is limited to what is necessary for
              security investigations, legal compliance, or direct user support with
              your consent.</li>
          </ul>
        </Section>

        <Section title="5. Data Retention and Deletion">
          <p>
            Your data is retained for as long as your account is active. You can delete your
            account at any time from the Settings page, which will permanently remove your
            account data, conversations, and ingested papers from our systems.
          </p>
          <p>
            To request data deletion without signing in, contact us at{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=Data Deletion Request`}
              className="underline underline-offset-2 hover:text-stone-900 transition-colors"
            >
              {CONTACT_EMAIL}
            </a>.
          </p>
        </Section>

        <Section title="6. Cookies and Local Storage">
          <p>
            Arxivian uses cookies set by Clerk for authentication sessions. We also use browser
            local storage to persist your display and model preferences. We do not use
            tracking cookies or third-party analytics cookies.
          </p>
        </Section>

        <Section title="7. Security">
          <p>
            We use industry-standard measures to protect your data, including encrypted
            connections (TLS), secure authentication via Clerk, and isolated database access.
            However, no method of transmission over the internet is 100% secure.
          </p>
        </Section>

        <Section title="8. Children's Privacy">
          <p>
            Arxivian is not directed at children under 13. We do not knowingly collect personal
            information from children. If you believe a child has provided us with personal
            data, please contact us and we will delete it.
          </p>
        </Section>

        <Section title="9. Changes to This Policy">
          <p>
            We may update this policy from time to time. If we make material changes, we will
            notify you by updating the date at the top of this page. Your continued use of
            Arxivian after changes constitutes acceptance of the updated policy.
          </p>
        </Section>

        <Section title="10. Contact">
          <p>
            If you have questions about this privacy policy or your data, contact us at{' '}
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=Privacy Policy Inquiry`}
              className="underline underline-offset-2 hover:text-stone-900 transition-colors"
            >
              {CONTACT_EMAIL}
            </a>.
          </p>
        </Section>
      </article>

      <Footer />
    </div>
  )
}

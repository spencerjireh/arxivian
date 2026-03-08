import { ChevronDown } from 'lucide-react'
import PublicHeader from '../components/layout/PublicHeader'
import Footer from '../components/layout/Footer'

const CONTACT_EMAIL = 'email@spencerjireh.com'
const EFFECTIVE_DATE = 'March 8, 2026'

interface SectionProps {
  id: string
  title: string
  children: React.ReactNode
}

function Section({ id, title, children }: SectionProps) {
  return (
    <section id={id} className="scroll-mt-24 animate-fade-in">
      <h2 className="font-display text-lg font-semibold text-stone-900 mb-3">
        {title}
      </h2>
      <div className="text-sm text-stone-600 leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  )
}

function ExternalLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="underline underline-offset-2 hover:text-stone-900 transition-colors"
    >
      {children}
    </a>
  )
}

function AnchorLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="underline underline-offset-2 hover:text-stone-900 transition-colors"
    >
      {children}
    </a>
  )
}

const TOC_ITEMS = [
  { id: 'info-collect', label: '1. What Information Do We Collect?' },
  { id: 'info-use', label: '2. How Do We Process Your Information?' },
  { id: 'legal-bases', label: '3. What Legal Bases Do We Rely On?' },
  { id: 'who-share', label: '4. When and With Whom Do We Share Your Information?' },
  { id: 'cookies', label: '5. Cookies and Other Tracking Technologies' },
  { id: 'ai', label: '6. Artificial Intelligence-Based Products' },
  { id: 'social-logins', label: '7. How Do We Handle Your Social Logins?' },
  { id: 'google-disclosure', label: '8. Google User Data Disclosure' },
  { id: 'data-retention', label: '9. Data Retention and Deletion' },
  { id: 'info-safe', label: '10. How Do We Keep Your Information Safe?' },
  { id: 'info-minors', label: '11. Do We Collect Information from Minors?' },
  { id: 'privacy-rights', label: '12. What Are Your Privacy Rights?' },
  { id: 'us-laws', label: '13. US Residents Privacy Rights' },
  { id: 'policy-updates', label: '14. Changes to This Policy' },
  { id: 'contact', label: '15. Contact' },
]

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
        <div
          style={{ '--stagger-index': 1 } as React.CSSProperties}
          className="text-sm text-stone-600 leading-relaxed space-y-3 animate-stagger"
        >
          <p>
            This Privacy Notice for Arxivian (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;),
            describes how and why we might access, collect, store, use, and/or share
            (&quot;process&quot;) your personal information when you use our services
            (&quot;Services&quot;), including when you:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>
              Visit our website at{' '}
              <ExternalLink href="https://arxivian.com">arxivian.com</ExternalLink>{' '}
              or any website of ours that links to this Privacy Notice
            </li>
            <li>
              Use Arxivian -- an AI-powered research assistant for analyzing academic papers
              from arXiv
            </li>
            <li>
              Engage with us in other related ways, including any marketing or events
            </li>
          </ul>
          <p>
            <strong className="text-stone-800">Questions or concerns?</strong>{' '}
            Reading this Privacy Notice will help you understand your privacy rights and choices.
            If you do not agree with our policies and practices, please do not use our Services.
          </p>
        </div>

        {/* Summary of Key Points */}
        <details className="animate-fade-in group">
          <summary className="flex items-center justify-between font-display text-lg font-semibold text-stone-900 mb-3 cursor-pointer list-none [&::-webkit-details-marker]:hidden">
            <span>Summary of Key Points</span>
            <ChevronDown
              className="w-5 h-5 text-stone-400 group-hover:text-stone-600 transition-transform duration-200 group-open:rotate-180"
              strokeWidth={2}
            />
          </summary>
          <div className="text-sm text-stone-600 leading-relaxed space-y-3 animate-fade-in">
              <p className="italic text-stone-500">
                This summary provides key points from our Privacy Notice. You can find more
                details by clicking the links or using the table of contents below.
              </p>
              <ul className="space-y-2">
                <li>
                  <strong className="text-stone-800">What personal information do we process?</strong>{' '}
                  When you visit, use, or navigate our Services, we may process personal information
                  depending on how you interact with us.{' '}
                  <AnchorLink href="#info-collect">Learn more</AnchorLink>.
                </li>
                <li>
                  <strong className="text-stone-800">Do we process any sensitive personal information?</strong>{' '}
                  We do not process sensitive personal information.
                </li>
                <li>
                  <strong className="text-stone-800">Do we collect any information from third parties?</strong>{' '}
                  We do not collect any information from third parties.
                </li>
                <li>
                  <strong className="text-stone-800">How do we process your information?</strong>{' '}
                  We process your information to provide, improve, and administer our Services,
                  communicate with you, for security and fraud prevention, and to comply with law.{' '}
                  <AnchorLink href="#info-use">Learn more</AnchorLink>.
                </li>
                <li>
                  <strong className="text-stone-800">In what situations and with which parties do we share personal information?</strong>{' '}
                  We may share information in specific situations and with specific third parties.{' '}
                  <AnchorLink href="#who-share">Learn more</AnchorLink>.
                </li>
                <li>
                  <strong className="text-stone-800">How do we keep your information safe?</strong>{' '}
                  We have adequate organizational and technical processes in place to protect your
                  personal information. However, no electronic transmission over the internet can be
                  guaranteed to be 100% secure.{' '}
                  <AnchorLink href="#info-safe">Learn more</AnchorLink>.
                </li>
                <li>
                  <strong className="text-stone-800">What are your rights?</strong>{' '}
                  Depending on where you are located geographically, the applicable privacy law
                  may mean you have certain rights regarding your personal information.{' '}
                  <AnchorLink href="#privacy-rights">Learn more</AnchorLink>.
                </li>
                <li>
                  <strong className="text-stone-800">How do you exercise your rights?</strong>{' '}
                  The easiest way to exercise your rights is by contacting us at{' '}
                  <AnchorLink href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</AnchorLink>.
                </li>
              </ul>
            </div>
        </details>

        {/* Table of Contents */}
        <nav className="animate-fade-in">
          <h2 className="font-display text-lg font-semibold text-stone-900 mb-3">
            Table of Contents
          </h2>
          <ol className="text-sm text-stone-600 leading-relaxed space-y-1.5 list-none">
            {TOC_ITEMS.map((item) => (
              <li key={item.id}>
                <AnchorLink href={`#${item.id}`}>{item.label}</AnchorLink>
              </li>
            ))}
          </ol>
        </nav>

        {/* 1. What Information Do We Collect? */}
        <Section id="info-collect" title="1. What Information Do We Collect?">
          <h3 className="font-display text-base font-medium text-stone-800">
            Personal information you disclose to us
          </h3>
          <p className="italic text-stone-500">
            In Short: We collect personal information that you provide to us.
          </p>
          <p>
            We collect personal information that you voluntarily provide to us when you register
            on the Services, express an interest in obtaining information about us or our products
            and Services, when you participate in activities on the Services, or otherwise when
            you contact us.
          </p>
          <p>
            <strong className="text-stone-800">Personal Information Provided by You.</strong>{' '}
            The personal information that we collect depends on the context of your interactions
            with us and the Services, the choices you make, and the products and features you use.
            The personal information we collect may include the following:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Names</li>
            <li>Email addresses</li>
            <li>Profile pictures</li>
            <li>Contact or authentication data</li>
          </ul>
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
          <p>
            <strong className="text-stone-800">Sensitive Information.</strong>{' '}
            We do not process sensitive information.
          </p>
          <p>
            <strong className="text-stone-800">Social Media Login Data.</strong>{' '}
            We may provide you with the option to register with us using your existing social
            media account details. If you choose to register in this way, we will collect certain
            profile information about you from the social media provider, as described in the
            section called{' '}
            <AnchorLink href="#social-logins">
              How Do We Handle Your Social Logins?
            </AnchorLink>{' '}
            below.
          </p>
          <p>
            <strong className="text-stone-800">Google API.</strong>{' '}
            Our use of information received from Google APIs adheres to the{' '}
            <ExternalLink href="https://developers.google.com/terms/api-services-user-data-policy">
              Google API Services User Data Policy
            </ExternalLink>, including the{' '}
            <ExternalLink href="https://developers.google.com/terms/api-services-user-data-policy#limited-use">
              Limited Use requirements
            </ExternalLink>.
          </p>
          <p>
            All personal information that you provide to us must be true, complete, and accurate,
            and you must notify us of any changes to such personal information.
          </p>
        </Section>

        {/* 2. How Do We Process Your Information? */}
        <Section id="info-use" title="2. How Do We Process Your Information?">
          <p className="italic text-stone-500">
            In Short: We process your information to provide, improve, and administer our
            Services, communicate with you, for security and fraud prevention, and to comply
            with law. We may also process your information for other purposes only with your
            prior explicit consent.
          </p>
          <p>
            We process your personal information for a variety of reasons, depending on how
            you interact with our Services, including:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>
              <strong className="text-stone-800">To facilitate account creation and authentication
              and otherwise manage user accounts.</strong>{' '}
              We may process your information so you can create and log in to your account, as
              well as keep your account in working order.
            </li>
            <li>
              <strong className="text-stone-800">To deliver and facilitate delivery of services
              to the user.</strong>{' '}
              We may process your information to provide you with the requested service.
            </li>
            <li>
              <strong className="text-stone-800">To respond to user inquiries/offer support to
              users.</strong>{' '}
              We may process your information to respond to your inquiries and solve any
              potential issues you might have with the requested service.
            </li>
            <li>
              <strong className="text-stone-800">To protect our Services.</strong>{' '}
              We may process your information as part of our efforts to keep our Services safe
              and secure, including fraud monitoring and prevention.
            </li>
            <li>
              <strong className="text-stone-800">To identify usage trends.</strong>{' '}
              We may process information about how you use our Services to better understand
              how they are being used so we can improve them.
            </li>
            <li>
              <strong className="text-stone-800">To improve response quality.</strong>{' '}
              We use self-hosted observability tooling (Langfuse) to monitor and improve the
              quality of AI-generated responses. Traces are stored on our own infrastructure.
            </li>
            <li>
              <strong className="text-stone-800">To save or protect an individual&apos;s vital
              interest.</strong>{' '}
              We may process your information when necessary to save or protect an
              individual&apos;s vital interest, such as to prevent harm.
            </li>
          </ul>
          <p>
            We do not sell your personal data. We do not use your data for advertising.
          </p>
        </Section>

        {/* 3. What Legal Bases Do We Rely On? */}
        <Section id="legal-bases" title="3. What Legal Bases Do We Rely On to Process Your Information?">
          <p className="italic text-stone-500">
            In Short: We only process your personal information when we believe it is necessary
            and we have a valid legal reason (i.e., legal basis) to do so under applicable law,
            like with your consent, to comply with laws, to provide you with services to enter
            into or fulfill our contractual obligations, to protect your rights, or to fulfill
            our legitimate business interests.
          </p>

          <h3 className="font-display text-base font-medium text-stone-800 italic">
            If you are located in the EU or UK, this section applies to you.
          </h3>
          <p>
            The General Data Protection Regulation (GDPR) and UK GDPR require us to explain
            the valid legal bases we rely on in order to process your personal information. As
            such, we may rely on the following legal bases to process your personal information:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>
              <strong className="text-stone-800">Consent.</strong>{' '}
              We may process your information if you have given us permission (i.e., consent)
              to use your personal information for a specific purpose. You can withdraw your
              consent at any time. Learn more about{' '}
              <AnchorLink href="#privacy-rights">withdrawing your consent</AnchorLink>.
            </li>
            <li>
              <strong className="text-stone-800">Performance of a Contract.</strong>{' '}
              We may process your personal information when we believe it is necessary to
              fulfill our contractual obligations to you, including providing our Services or
              at your request prior to entering into a contract with you.
            </li>
            <li>
              <strong className="text-stone-800">Legitimate Interests.</strong>{' '}
              We may process your information when we believe it is reasonably necessary to
              achieve our legitimate business interests and those interests do not outweigh
              your interests and fundamental rights and freedoms. For example, we may process
              your personal information for some of the purposes described in order to:
              <ul className="list-disc list-inside ml-4 mt-1.5 space-y-1">
                <li>Analyze how our Services are used so we can improve them to engage and retain users</li>
                <li>Diagnose problems and/or prevent fraudulent activities</li>
              </ul>
            </li>
            <li>
              <strong className="text-stone-800">Legal Obligations.</strong>{' '}
              We may process your information where we believe it is necessary for compliance
              with our legal obligations, such as to cooperate with a law enforcement body or
              regulatory agency, exercise or defend our legal rights, or disclose your
              information as evidence in litigation in which we are involved.
            </li>
            <li>
              <strong className="text-stone-800">Vital Interests.</strong>{' '}
              We may process your information where we believe it is necessary to protect your
              vital interests or the vital interests of a third party, such as situations
              involving potential threats to the safety of any person.
            </li>
          </ul>

          <h3 className="font-display text-base font-medium text-stone-800 italic">
            If you are located in Canada, this section applies to you.
          </h3>
          <p>
            We may process your information if you have given us specific permission (i.e.,
            express consent) to use your personal information for a specific purpose, or in
            situations where your permission can be inferred (i.e., implied consent). You
            can{' '}
            <AnchorLink href="#privacy-rights">withdraw your consent</AnchorLink>{' '}
            at any time.
          </p>
          <p>
            In some exceptional cases, we may be legally permitted under applicable law to
            process your information without your consent, including, for example:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>If collection is clearly in the interests of an individual and consent cannot be obtained in a timely way</li>
            <li>For investigations and fraud detection and prevention</li>
            <li>For business transactions provided certain conditions are met</li>
            <li>If it is contained in a witness statement and the collection is necessary to assess, process, or settle an insurance claim</li>
            <li>For identifying injured, ill, or deceased persons and communicating with next of kin</li>
            <li>If we have reasonable grounds to believe an individual has been, is, or may be victim of financial abuse</li>
            <li>If it is reasonable to expect collection and use with consent would compromise the availability or the accuracy of the information and the collection is reasonable for purposes related to investigating a breach of an agreement or a contravention of the laws of Canada or a province</li>
            <li>If disclosure is required to comply with a subpoena, warrant, court order, or rules of the court relating to the production of records</li>
            <li>If it was produced by an individual in the course of their employment, business, or profession and the collection is consistent with the purposes for which the information was produced</li>
            <li>If the collection is solely for journalistic, artistic, or literary purposes</li>
            <li>If the information is publicly available and is specified by the regulations</li>
          </ul>
        </Section>

        {/* 4. When and With Whom Do We Share Your Information? */}
        <Section id="who-share" title="4. When and With Whom Do We Share Your Information?">
          <p className="italic text-stone-500">
            In Short: We may share information in specific situations described in this section
            and/or with the following third parties.
          </p>
          <p>
            <strong className="text-stone-800">Vendors, Consultants, and Other Third-Party
            Service Providers.</strong>{' '}
            We may share your data with third-party vendors, service providers, contractors, or
            agents (&quot;third parties&quot;) who perform services for us or on our behalf and
            require access to such information to do that work. We have contracts in place with
            our third parties, which are designed to help safeguard your personal information.
          </p>
          <p>
            The third parties we may share personal information with are as follows:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>
              <strong className="text-stone-800">Clerk</strong> -- authentication and user
              management. Subject to{' '}
              <ExternalLink href="https://clerk.com/legal/privacy">
                Clerk&apos;s Privacy Policy
              </ExternalLink>.
            </li>
            <li>
              <strong className="text-stone-800">OpenAI</strong> -- language model inference for
              generating responses. Your conversation messages are sent to OpenAI&apos;s API for
              processing. Subject to{' '}
              <ExternalLink href="https://openai.com/policies/privacy-policy">
                OpenAI&apos;s Privacy Policy
              </ExternalLink>.
            </li>
            <li>
              <strong className="text-stone-800">NVIDIA NIM</strong> -- language model inference
              as an alternative provider. Conversation messages may be sent to NVIDIA&apos;s API
              depending on model selection. Subject to{' '}
              <ExternalLink href="https://www.nvidia.com/en-us/about-nvidia/privacy-policy/">
                NVIDIA&apos;s Privacy Policy
              </ExternalLink>.
            </li>
            <li>
              <strong className="text-stone-800">Jina AI</strong> -- text embedding service used
              to convert paper content into vector representations for search and retrieval.
              Paper text is sent to Jina&apos;s API for embedding. Subject to{' '}
              <ExternalLink href="https://jina.ai/legal/#privacy-policy">
                Jina AI&apos;s Privacy Policy
              </ExternalLink>.
            </li>
            <li>
              <strong className="text-stone-800">Langfuse</strong> -- self-hosted LLM
              observability for monitoring response quality. Traces are stored on our own
              infrastructure.
            </li>
            <li>
              <strong className="text-stone-800">arXiv</strong> -- paper metadata and content
              retrieval. We access publicly available papers through arXiv&apos;s API.
            </li>
          </ul>
          <p>
            We also may need to share your personal information in the following situations:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>
              <strong className="text-stone-800">Business Transfers.</strong>{' '}
              We may share or transfer your information in connection with, or during
              negotiations of, any merger, sale of company assets, financing, or acquisition
              of all or a portion of our business to another company.
            </li>
          </ul>
        </Section>

        {/* 5. Cookies and Other Tracking Technologies */}
        <Section id="cookies" title="5. Do We Use Cookies and Other Tracking Technologies?">
          <p className="italic text-stone-500">
            In Short: We use cookies set by Clerk for authentication and browser local storage
            for your preferences. We do not use tracking or analytics cookies.
          </p>
          <p>
            Arxivian uses cookies set by Clerk for authentication sessions. We also use browser
            local storage to persist your display and model preferences. We do not use
            tracking cookies, third-party analytics cookies, or advertising cookies.
          </p>
          <p>
            We do not permit third parties or service providers to use online tracking
            technologies on our Services for analytics or advertising purposes.
          </p>
          <p>
            <strong className="text-stone-800">Do-Not-Track.</strong>{' '}
            Most web browsers and some mobile operating systems include a Do-Not-Track
            (&quot;DNT&quot;) feature or setting. At this stage, no uniform technology standard
            for recognizing and implementing DNT signals has been finalized. As such, we do not
            currently respond to DNT browser signals or any other mechanism that automatically
            communicates your choice not to be tracked online. Because we do not use tracking
            cookies, this has no practical impact on your experience. If a standard for online
            tracking is adopted that we must follow in the future, we will inform you about that
            practice in a revised version of this Privacy Notice.
          </p>
        </Section>

        {/* 6. AI-Based Products */}
        <Section id="ai" title="6. Do We Offer Artificial Intelligence-Based Products?">
          <p className="italic text-stone-500">
            In Short: We offer products, features, or tools powered by artificial intelligence,
            machine learning, or similar technologies.
          </p>
          <p>
            As part of our Services, we offer products, features, or tools powered by artificial
            intelligence, machine learning, or similar technologies (collectively, &quot;AI
            Products&quot;). These tools are designed to enhance your experience and provide you
            with innovative solutions. The terms in this Privacy Notice govern your use of the
            AI Products within our Services.
          </p>
          <p>
            <strong className="text-stone-800">Use of AI Technologies.</strong>{' '}
            We provide the AI Products through third-party service providers (&quot;AI Service
            Providers&quot;), including OpenAI and NVIDIA AI. As outlined in this Privacy
            Notice, your input, output, and personal information will be shared with and
            processed by these AI Service Providers to enable your use of our AI Products for
            purposes outlined in{' '}
            <AnchorLink href="#legal-bases">
              What Legal Bases Do We Rely On to Process Your Information?
            </AnchorLink>{' '}
            You must not use the AI Products in any way that violates the terms or policies of
            any AI Service Provider.
          </p>
          <p>
            <strong className="text-stone-800">Our AI Products.</strong>{' '}
            Our AI Products are designed for the following functions:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Natural language processing</li>
            <li>Text analysis</li>
            <li>Academic paper retrieval and citation exploration</li>
          </ul>
          <p>
            <strong className="text-stone-800">How We Process Your Data Using AI.</strong>{' '}
            All personal information processed using our AI Products is handled in line with
            our Privacy Notice and our agreement with third parties. This ensures high security
            and safeguards your personal information throughout the process.
          </p>
          <p>
            <strong className="text-stone-800">How to Opt Out.</strong>{' '}
            To opt out of AI-powered features, you can:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Log in to your account settings and update your user account</li>
            <li>Contact us using the contact information provided</li>
          </ul>
        </Section>

        {/* 7. Social Logins */}
        <Section id="social-logins" title="7. How Do We Handle Your Social Logins?">
          <p className="italic text-stone-500">
            In Short: If you choose to register or log in to our Services using a social media
            account, we may have access to certain information about you.
          </p>
          <p>
            Our Services offer you the ability to register and log in using your third-party
            social media account details (like your Google account). Where you choose to do
            this, we will receive certain profile information about you from your social media
            provider. The profile information we receive may vary depending on the social media
            provider concerned, but will often include your name, email address, and profile
            picture, as well as other information you choose to make public on such a social
            media platform.
          </p>
          <p>
            We will use the information we receive only for the purposes that are described in
            this Privacy Notice or that are otherwise made clear to you on the relevant
            Services. Please note that we do not control, and are not responsible for, other
            uses of your personal information by your third-party social media provider. We
            recommend that you review their privacy notice to understand how they collect, use,
            and share your personal information, and how you can set your privacy preferences
            on their sites and apps.
          </p>
        </Section>

        {/* 8. Google User Data Disclosure */}
        <Section id="google-disclosure" title="8. Google User Data Disclosure">
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
            Arxivian&apos;s use and transfer of information received from Google APIs adheres to
            the{' '}
            <ExternalLink href="https://developers.google.com/terms/api-services-user-data-policy">
              Google API Services User Data Policy
            </ExternalLink>, including the Limited Use requirements. Specifically:
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

        {/* 9. Data Retention and Deletion */}
        <Section id="data-retention" title="9. Data Retention and Deletion">
          <p className="italic text-stone-500">
            In Short: We keep your information for as long as necessary to fulfill the purposes
            outlined in this Privacy Notice unless otherwise required by law.
          </p>
          <p>
            We will only keep your personal information for as long as it is necessary for the
            purposes set out in this Privacy Notice, unless a longer retention period is required
            or permitted by law (such as tax, accounting, or other legal requirements). No
            purpose in this notice will require us keeping your personal information for longer
            than the period of time in which users have an account with us.
          </p>
          <p>
            When we have no ongoing legitimate business need to process your personal
            information, we will either delete or anonymize such information, or, if this is
            not possible (for example, because your personal information has been stored in
            backup archives), then we will securely store your personal information and isolate
            it from any further processing until deletion is possible.
          </p>
          <p>
            You can delete your account at any time from the Settings page, which will
            permanently remove your account data, conversations, and ingested papers from
            our systems.
          </p>
          <p>
            To request data deletion without signing in, contact us at{' '}
            <AnchorLink href={`mailto:${CONTACT_EMAIL}?subject=Data Deletion Request`}>
              {CONTACT_EMAIL}
            </AnchorLink>.
          </p>
        </Section>

        {/* 10. How Do We Keep Your Information Safe? */}
        <Section id="info-safe" title="10. How Do We Keep Your Information Safe?">
          <p className="italic text-stone-500">
            In Short: We aim to protect your personal information through a system of
            organizational and technical security measures.
          </p>
          <p>
            We have implemented appropriate and reasonable technical and organizational security
            measures designed to protect the security of any personal information we process,
            including encrypted connections (TLS), secure authentication via Clerk, and isolated
            database access.
          </p>
          <p>
            However, despite our safeguards and efforts to secure your information, no
            electronic transmission over the Internet or information storage technology can be
            guaranteed to be 100% secure, so we cannot promise or guarantee that hackers,
            cybercriminals, or other unauthorized third parties will not be able to defeat our
            security and improperly collect, access, steal, or modify your information. Although
            we will do our best to protect your personal information, transmission of personal
            information to and from our Services is at your own risk. You should only access the
            Services within a secure environment.
          </p>
        </Section>

        {/* 11. Do We Collect Information from Minors? */}
        <Section id="info-minors" title="11. Do We Collect Information from Minors?">
          <p className="italic text-stone-500">
            In Short: We do not knowingly collect data from or market to children under 18 years
            of age or the equivalent age as specified by law in your jurisdiction.
          </p>
          <p>
            We do not knowingly collect, solicit data from, or market to children under 18
            years of age or the equivalent age as specified by law in your jurisdiction, nor
            do we knowingly sell such personal information. By using the Services, you represent
            that you are at least 18 or the equivalent age as specified by law in your
            jurisdiction or that you are the parent or guardian of such a minor and consent to
            such minor dependent&apos;s use of the Services. If we learn that personal
            information from users less than 18 years of age or the equivalent age as specified
            by law in your jurisdiction has been collected, we will deactivate the account and
            take reasonable measures to promptly delete such data from our records. If you
            become aware of any data we may have collected from children under age 18 or the
            equivalent age as specified by law in your jurisdiction, please contact us at{' '}
            <AnchorLink href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</AnchorLink>.
          </p>
        </Section>

        {/* 12. What Are Your Privacy Rights? */}
        <Section id="privacy-rights" title="12. What Are Your Privacy Rights?">
          <p className="italic text-stone-500">
            In Short: Depending on your state of residence in the US or in some regions, such as
            the European Economic Area (EEA), United Kingdom (UK), Switzerland, and Canada, you
            have rights that allow you greater access to and control over your personal
            information. You may review, change, or terminate your account at any time.
          </p>
          <p>
            In some regions (like the EEA, UK, Switzerland, and Canada), you have certain rights
            under applicable data protection laws. These may include the right (i) to request
            access and obtain a copy of your personal information, (ii) to request rectification
            or erasure; (iii) to restrict the processing of your personal information; (iv) if
            applicable, to data portability; and (v) not to be subject to automated
            decision-making. If a decision that produces legal or similarly significant effects
            is made solely by automated means, we will inform you, explain the main factors,
            and offer a simple way to request human review. In certain circumstances, you may
            also have the right to object to the processing of your personal information. You
            can make such a request by contacting us using the contact details provided in the
            section <AnchorLink href="#contact">Contact</AnchorLink> below.
          </p>
          <p>
            We will consider and act upon any request in accordance with applicable data
            protection laws.
          </p>
          <p>
            If you are located in the EEA or UK and you believe we are unlawfully processing
            your personal information, you also have the right to complain to your{' '}
            <ExternalLink href="https://ec.europa.eu/justice/data-protection/bodies/authorities/index_en.htm">
              Member State data protection authority
            </ExternalLink>{' '}
            or{' '}
            <ExternalLink href="https://ico.org.uk/make-a-complaint/data-protection-complaints/data-protection-complaints/">
              UK data protection authority
            </ExternalLink>.
          </p>
          <p>
            If you are located in Switzerland, you may contact the{' '}
            <ExternalLink href="https://www.edoeb.admin.ch/edoeb/en/home.html">
              Federal Data Protection and Information Commissioner
            </ExternalLink>.
          </p>
          <p>
            <strong className="text-stone-800">Withdrawing your consent:</strong>{' '}
            If we are relying on your consent to process your personal information, which may be
            express and/or implied consent depending on the applicable law, you have the right to
            withdraw your consent at any time. You can withdraw your consent at any time by
            contacting us using the contact details provided in the
            section <AnchorLink href="#contact">Contact</AnchorLink> below.
          </p>
          <p>
            However, please note that this will not affect the lawfulness of the processing
            before its withdrawal nor, when applicable law allows, will it affect the processing
            of your personal information conducted in reliance on lawful processing grounds
            other than consent.
          </p>
          <p>
            <strong className="text-stone-800">Account Information.</strong>{' '}
            If you would at any time like to review or change the information in your account
            or terminate your account, you can:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Log in to your account settings and update your user account.</li>
            <li>Contact us using the contact information provided.</li>
          </ul>
          <p>
            Upon your request to terminate your account, we will deactivate or delete your
            account and information from our active databases. However, we may retain some
            information in our files to prevent fraud, troubleshoot problems, assist with any
            investigations, enforce our legal terms and/or comply with applicable legal
            requirements.
          </p>
        </Section>

        {/* 13. US Residents Privacy Rights */}
        <Section id="us-laws" title="13. Do United States Residents Have Specific Privacy Rights?">
          <p className="italic text-stone-500">
            In Short: If you are a resident of a US state with applicable privacy laws, you may
            have the right to request access to and receive details about the personal
            information we maintain about you and how we have processed it, correct inaccuracies,
            get a copy of, or delete your personal information. You may also have the right to
            withdraw your consent to our processing of your personal information.
          </p>

          <h3 className="font-display text-base font-medium text-stone-800">
            Categories of Personal Information We Collect
          </h3>
          <p>
            The table below shows the categories of personal information we have collected in
            the past twelve (12) months.
          </p>
          <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-stone-200">
                  <th className="text-left py-2 pr-4 font-medium text-stone-800">Category</th>
                  <th className="text-left py-2 pr-4 font-medium text-stone-800">Examples</th>
                  <th className="text-left py-2 font-medium text-stone-800">Collected</th>
                </tr>
              </thead>
              <tbody className="text-stone-600">
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">A. Identifiers</td>
                  <td className="py-2 pr-4 align-top">Contact details, such as real name, alias, email address, and account name</td>
                  <td className="py-2 align-top font-medium text-stone-800">YES</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">B. Protected classification characteristics</td>
                  <td className="py-2 pr-4 align-top">Gender, age, date of birth, race and ethnicity, national origin, marital status</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">C. Commercial information</td>
                  <td className="py-2 pr-4 align-top">Transaction information, purchase history, financial details, and payment information</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">D. Biometric information</td>
                  <td className="py-2 pr-4 align-top">Fingerprints and voiceprints</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">E. Internet or other similar network activity</td>
                  <td className="py-2 pr-4 align-top">Browsing history, search history, online behavior, interest data</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">F. Geolocation data</td>
                  <td className="py-2 pr-4 align-top">Device location</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">G. Audio, electronic, sensory, or similar information</td>
                  <td className="py-2 pr-4 align-top">Images and audio, video or call recordings</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">H. Professional or employment-related information</td>
                  <td className="py-2 pr-4 align-top">Business contact details, job title, work history</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">I. Education Information</td>
                  <td className="py-2 pr-4 align-top">Student records and directory information</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">J. Inferences drawn from collected personal information</td>
                  <td className="py-2 pr-4 align-top">Inferences drawn to create a profile about preferences and characteristics</td>
                  <td className="py-2 align-top">NO</td>
                </tr>
                <tr className="border-b border-stone-100">
                  <td className="py-2 pr-4 align-top">K. Sensitive personal Information</td>
                  <td className="py-2 pr-4 align-top"></td>
                  <td className="py-2 align-top">NO</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            We may also collect other personal information outside of these categories through
            instances where you interact with us in person, online, or by phone or mail in the
            context of:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Receiving help through our customer support channels</li>
            <li>Participation in customer surveys or contests</li>
            <li>Facilitation in the delivery of our Services and to respond to your inquiries</li>
          </ul>
          <p>
            We have not sold or shared any personal information to third parties for a business
            or commercial purpose in the preceding twelve (12) months.
          </p>

          <h3 className="font-display text-base font-medium text-stone-800">Your Rights</h3>
          <p>
            You have rights under certain US state data protection laws. However, these rights
            are not absolute, and in certain cases, we may decline your request as permitted by
            law. These rights include:
          </p>
          <ul className="list-disc list-inside space-y-1.5">
            <li>Right to know whether or not we are processing your personal data</li>
            <li>Right to access your personal data</li>
            <li>Right to correct inaccuracies in your personal data</li>
            <li>Right to request the deletion of your personal data</li>
            <li>Right to obtain a copy of the personal data you previously shared with us</li>
            <li>Right to non-discrimination for exercising your rights</li>
            <li>Right to opt out of the processing of your personal data if it is used for targeted advertising, the sale of personal data, or profiling in furtherance of decisions that produce legal or similarly significant effects (&quot;profiling&quot;)</li>
          </ul>
          <p>
            <strong className="text-stone-800">How to Exercise Your Rights.</strong>{' '}
            To exercise these rights, you can contact us by emailing us at{' '}
            <AnchorLink href={`mailto:${CONTACT_EMAIL}?subject=Privacy Rights Request`}>
              {CONTACT_EMAIL}
            </AnchorLink>, or by referring to the contact details at the bottom of this document.
          </p>
          <p>
            Under certain US state data protection laws, you can designate an authorized agent
            to make a request on your behalf. We may deny a request from an authorized agent
            that does not submit proof that they have been validly authorized to act on your
            behalf in accordance with applicable laws.
          </p>
          <p>
            <strong className="text-stone-800">Request Verification.</strong>{' '}
            Upon receiving your request, we will need to verify your identity to determine you
            are the same person about whom we have the information in our system. We will only
            use personal information provided in your request to verify your identity or
            authority to make the request. However, if we cannot verify your identity from the
            information already maintained by us, we may request that you provide additional
            information for the purposes of verifying your identity and for security or
            fraud-prevention purposes.
          </p>
        </Section>

        {/* 14. Changes to This Policy */}
        <Section id="policy-updates" title="14. Changes to This Policy">
          <p>
            We may update this policy from time to time. If we make material changes, we will
            notify you by updating the date at the top of this page. Your continued use of
            Arxivian after changes constitutes acceptance of the updated policy.
          </p>
        </Section>

        {/* 15. Contact */}
        <Section id="contact" title="15. Contact">
          <p>
            If you have questions about this privacy policy or your data, contact us at{' '}
            <AnchorLink href={`mailto:${CONTACT_EMAIL}?subject=Privacy Policy Inquiry`}>
              {CONTACT_EMAIL}
            </AnchorLink>.
          </p>
        </Section>
      </article>

      <Footer />
    </div>
  )
}

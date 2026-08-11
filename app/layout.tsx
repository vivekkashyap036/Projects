import type { Metadata } from 'next'
import { Inter, Playfair_Display } from 'next/font/google'
import './globals.css'
import Header from '@/components/Header'

const inter = Inter({
  variable: '--font-body',
  subsets: ['latin'],
})

const playfair = Playfair_Display({
  variable: '--font-heading',
  subsets: ['latin'],
})

// Every page depends on the live Supabase session, so nothing here is
// statically prerenderable — this also lets `next build` succeed without
// real Supabase credentials present.
export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: {
    default: 'Callsheet — The network for film industry professionals',
    template: '%s | Callsheet',
  },
  description:
    'Find and connect with actors, directors, producers, cinematographers, and crew of every kind.',
}

export default function RootLayout({ children }: LayoutProps<'/'>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${playfair.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-ink-950 text-ink-50">
        <Header />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  )
}

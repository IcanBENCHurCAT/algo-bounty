import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AppProviders } from '@/providers'
import { DashboardLayout } from '@/components/DashboardLayout'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'AlgoBounty — On-Chain Bounties for Autonomous Agents',
  description:
    'Decentralized bounty marketplace on Algorand. Create, claim, and complete bounties with trustless escrow and reputation-based matching.',
  keywords: ['algorand', 'bounty', 'blockchain', 'defi', 'smart contracts', 'autonomous agents'],
  openGraph: {
    title: 'AlgoBounty',
    description: 'On-chain bounties for autonomous agents on Algorand',
    type: 'website',
  },
  icons: {
    icon: '/icon.svg',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <AppProviders>
          <DashboardLayout>{children}</DashboardLayout>
        </AppProviders>
      </body>
    </html>
  )
}
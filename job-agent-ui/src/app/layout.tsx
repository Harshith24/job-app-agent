import type { Metadata } from 'next'
import { Outfit } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'

const outfit = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
})

export const metadata: Metadata = {
  title: 'Job Search AI Agent',
  description: 'AI-powered job search with personalized resume and cover letter generation',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${outfit.className} antialiased min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
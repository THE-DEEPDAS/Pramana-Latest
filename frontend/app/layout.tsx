import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'PowerMind - RAG Assistant',
  description: 'Retrieve and Generate intelligent responses with your documents',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-[#0f172a] text-[#f8fafc] antialiased">
        {children}
      </body>
    </html>
  )
}

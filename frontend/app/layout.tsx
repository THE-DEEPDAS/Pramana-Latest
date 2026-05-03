import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from '@/app/ThemeProvider'

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
      <body className="bg-[#f5efe4] text-gray-900 antialiased transition-colors dark:bg-[#0b1220] dark:text-gray-100">
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  )
}

'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import MainContent from '@/components/MainContent'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'chat' | 'upload'>('upload')

  return (
    <div className="flex h-screen bg-[#0f172a] text-[#f8fafc]">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <MainContent activeTab={activeTab} />
    </div>
  )
}

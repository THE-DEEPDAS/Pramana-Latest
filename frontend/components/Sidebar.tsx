import { Settings, FileText, MessageSquare, Home } from 'lucide-react'
import ThemeToggle from './ThemeToggle'

interface SidebarProps {
  activeTab: 'chat' | 'settings'
  setActiveTab: (tab: 'chat' | 'settings') => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  return (
    <aside className="w-64 bg-[#fbf6ec] dark:bg-[#0f172a] border-r border-[#e4d8c7] dark:border-[#22314f] flex flex-col h-screen shadow-[inset_-1px_0_0_rgba(255,255,255,0.03)] dark:shadow-[inset_-1px_0_0_rgba(59,130,246,0.08)]">
      {/* Header */}
      <div className="p-6 border-b border-[#e4d8c7] dark:border-[#22314f]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#bfa98b] dark:bg-gradient-to-br dark:from-[#3b82f6] dark:to-[#1d4ed8] flex items-center justify-center shadow-sm shadow-amber-500/20 dark:shadow-blue-500/20">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">PowerMind</h1>
            <p className="text-xs text-gray-600 dark:text-gray-400">RAG Assistant</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <button
          onClick={() => setActiveTab('chat')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            activeTab === 'chat'
              ? 'bg-gradient-to-r from-[#fff1cf] to-[#f7d98d] text-gray-900 shadow-md shadow-amber-500/20 dark:from-[#1e3a8a] dark:to-[#2563eb] dark:text-white dark:shadow-blue-500/15'
              : 'text-gray-700 dark:text-gray-200 hover:bg-[#f0e7d9] dark:hover:bg-[#14213a] hover:shadow-sm'
          }`}
        >
          <MessageSquare className="w-5 h-5" />
          <span className="font-medium">Chat</span>
        </button>

        <div className="h-px bg-[#e4d8c7] dark:bg-[#22314f] my-4" />

        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-[#f0e7d9] dark:hover:bg-[#14213a] transition-all duration-200 hover:shadow-sm">
          <Home className="w-5 h-5" />
          <span className="font-medium">Dashboard</span>
        </button>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#e4d8c7] dark:border-[#22314f] space-y-2">
        <div className="px-4 py-2">
          <ThemeToggle />
        </div>

        <button
          onClick={() => setActiveTab('settings')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
            activeTab === 'settings'
              ? 'bg-gradient-to-r from-[#fff1cf] to-[#f7d98d] text-gray-900 shadow-md shadow-amber-500/20 dark:from-[#1e3a8a] dark:to-[#2563eb] dark:text-white dark:shadow-blue-500/15'
              : 'text-gray-700 dark:text-gray-200 hover:bg-[#f0e7d9] dark:hover:bg-[#14213a] hover:shadow-sm'
          }`}
        >
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </button>

        <div className="px-4 py-2 bg-[#f0e7d9] dark:bg-[#14213a] rounded-lg border border-[#e0d3c1] dark:border-[#24406e]">
          <p className="text-xs text-gray-600 dark:text-blue-100/80 font-medium">Documents Indexed</p>
          <p className="text-sm text-gray-900 dark:text-gray-100 font-semibold mt-1">0</p>
        </div>
      </div>
    </aside>
  )
}

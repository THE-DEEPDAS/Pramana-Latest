import { Settings, FileText, MessageSquare, Home } from 'lucide-react'

interface SidebarProps {
  activeTab: 'chat' | 'upload'
  setActiveTab: (tab: 'chat' | 'upload') => void
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  return (
    <aside className="w-64 bg-[#1e293b] border-r border-[#334155] flex flex-col h-screen">
      {/* Header */}
      <div className="p-6 border-b border-[#334155]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#3b82f6] flex items-center justify-center">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#f8fafc]">PowerMind</h1>
            <p className="text-xs text-[#94a3b8]">RAG Assistant</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <button
          onClick={() => setActiveTab('upload')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
            activeTab === 'upload'
              ? 'bg-[#3b82f6] text-white'
              : 'text-[#cbd5e1] hover:bg-[#334155]'
          }`}
        >
          <FileText className="w-5 h-5" />
          <span className="font-medium">Upload Documents</span>
        </button>

        <button
          onClick={() => setActiveTab('chat')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
            activeTab === 'chat'
              ? 'bg-[#3b82f6] text-white'
              : 'text-[#cbd5e1] hover:bg-[#334155]'
          }`}
        >
          <MessageSquare className="w-5 h-5" />
          <span className="font-medium">Chat</span>
        </button>

        <div className="h-px bg-[#334155] my-4" />

        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-[#cbd5e1] hover:bg-[#334155] transition-colors">
          <Home className="w-5 h-5" />
          <span className="font-medium">Dashboard</span>
        </button>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-[#334155] space-y-2">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-[#cbd5e1] hover:bg-[#334155] transition-colors">
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </button>

        <div className="px-4 py-2 bg-[#334155] rounded-lg">
          <p className="text-xs text-[#94a3b8] font-medium">Documents Indexed</p>
          <p className="text-sm text-[#f8fafc] font-semibold mt-1">0</p>
        </div>
      </div>
    </aside>
  )
}

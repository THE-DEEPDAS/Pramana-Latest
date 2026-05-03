import ChatInterface from './ChatInterface'
import SettingsPanel from './SettingsPanel'

interface MainContentProps {
  activeTab: 'chat' | 'settings'
}

export default function MainContent({ activeTab }: MainContentProps) {
  return (
    <main className="flex-1 flex min-h-0 flex-col bg-[#f5efe4] dark:bg-[#0b1220] overflow-hidden transition-colors">
      <div className={activeTab === 'chat' ? 'flex-1 flex min-h-0 flex-col' : 'hidden'}>
        <ChatInterface selectedSources={[]} />
      </div>
      <div className={activeTab === 'settings' ? 'flex-1 flex min-h-0 flex-col' : 'hidden'}>
        <SettingsPanel />
      </div>
    </main>
  )
}

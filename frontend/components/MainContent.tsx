import FileUploadSection from './FileUploadSection'
import ChatInterface from './ChatInterface'

interface MainContentProps {
  activeTab: 'chat' | 'upload'
}

export default function MainContent({ activeTab }: MainContentProps) {
  return (
    <main className="flex-1 flex flex-col bg-[#0f172a] overflow-hidden">
      {activeTab === 'upload' && <FileUploadSection />}
      {activeTab === 'chat' && <ChatInterface />}
    </main>
  )
}

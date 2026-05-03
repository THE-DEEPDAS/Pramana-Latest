'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, FilePlus2, FileText, Search, Square, Trash2 } from 'lucide-react'
import type { UploadedSource } from '@/app/page'

interface SourcesPanelProps {
  sources: UploadedSource[]
  allSources: UploadedSource[]
  onSourcesChange: React.Dispatch<React.SetStateAction<UploadedSource[]>>
  searchTerm: string
  onSearchTermChange: (value: string) => void
  onSelectedSourceIdsChange: (ids: string[]) => void
  onPreviewSourceChange: (source: UploadedSource) => void
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${Math.round((bytes / Math.pow(k, i)) * 100) / 100} ${sizes[i]}`
}

export default function SourcesPanel({
  sources,
  allSources,
  onSourcesChange,
  searchTerm,
  onSearchTermChange,
  onSelectedSourceIdsChange,
  onPreviewSourceChange,
}: SourcesPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>(() =>
    allSources.length > 0 ? [allSources[0].id] : []
  )

  const selectedCount = selectedSourceIds.length
  const allVisibleSelected = sources.length > 0 && sources.every((source) => selectedSourceIds.includes(source.id))

  const displayedSources = useMemo(() => sources, [sources])

  useEffect(() => {
    onSelectedSourceIdsChange(selectedSourceIds)
  }, [onSelectedSourceIdsChange, selectedSourceIds])

  useEffect(() => {
    if (allSources.length > 0 && selectedSourceIds.length === 0) {
      setSelectedSourceIds([allSources[0].id])
    }
  }, [allSources, selectedSourceIds.length])

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files
    if (!selectedFiles?.length) return

    const addedSources = Array.from(selectedFiles).map((file) => ({
      id: `${file.name}-${Date.now()}`,
      name: file.name,
      size: file.size,
      status: 'uploading' as const,
      uploadedAt: new Date().toLocaleDateString(),
      previewUrl: file.type === 'application/pdf' ? URL.createObjectURL(file) : URL.createObjectURL(file),
    }))

    onSourcesChange((currentSources) => [...currentSources, ...addedSources])
    event.target.value = ''

    addedSources.forEach((source) => {
      window.setTimeout(() => {
        onSourcesChange((currentSources) =>
          currentSources.map((item) =>
            item.id === source.id ? { ...item, status: 'completed' as const } : item
          )
        )
      }, 1200)
    })
  }

  const removeSource = (id: string) => {
    setSelectedSourceIds((currentSelected) => currentSelected.filter((sourceId) => sourceId !== id))
    onSourcesChange((currentSources) => currentSources.filter((source) => source.id !== id))
  }

  const toggleSource = (id: string) => {
    setSelectedSourceIds((currentSelected) =>
      currentSelected.includes(id)
        ? currentSelected.filter((sourceId) => sourceId !== id)
        : [...currentSelected, id]
    )
  }

  const toggleAllVisibleSources = () => {
    if (allVisibleSelected) {
      setSelectedSourceIds((currentSelected) =>
        currentSelected.filter((sourceId) => !sources.some((source) => source.id === sourceId))
      )
      return
    }

    setSelectedSourceIds((currentSelected) => {
      const merged = new Set([...currentSelected, ...sources.map((source) => source.id)])
      return Array.from(merged)
    })
  }

  const openPreview = (source: UploadedSource) => {
    onPreviewSourceChange(source)
  }

  return (
    <aside className="flex w-[380px] flex-col border-r border-[#2e323b] bg-[#22252c] text-gray-100 shadow-[inset_-1px_0_0_rgba(255,255,255,0.03)]">
      <div className="flex items-center justify-between border-b border-[#313641] px-5 py-4">
        <h2 className="text-xl font-medium text-gray-100">Sources</h2>
        <button className="rounded-md p-1 text-gray-300 hover:bg-[#2d3139] hover:text-white" aria-label="Collapse sources panel">
          <ChevronDown className="h-5 w-5 -rotate-90" />
        </button>
      </div>

      <div className="space-y-4 p-4">
        <button
          onClick={() => inputRef.current?.click()}
          className="flex w-full items-center justify-center gap-3 rounded-full border border-[#3a3f49] bg-[#252930] px-4 py-4 text-base font-medium text-gray-100 transition-all hover:border-[#4a5160] hover:bg-[#2a2f37]"
        >
          <FilePlus2 className="h-5 w-5 text-gray-200" />
          Add sources
        </button>

        <input ref={inputRef} type="file" multiple className="hidden" onChange={handleFileSelect} accept=".pdf,.txt,.docx" />

        <div className="rounded-3xl border border-[#353a45] bg-[#1d2127] p-4 shadow-inner">
          <label className="flex items-start gap-3 text-gray-200">
            <Search className="mt-1 h-5 w-5 text-gray-400" />
            <input
              value={searchTerm}
              onChange={(event) => onSearchTermChange(event.target.value)}
              placeholder="Search saved sources"
              className="w-full bg-transparent text-lg leading-snug text-gray-200 outline-none placeholder:text-gray-400"
            />
          </label>

          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={toggleAllVisibleSources}
              className="rounded-full border border-[#3a3f49] bg-[#2a2f37] px-3 py-2 text-sm font-medium text-gray-100 transition hover:bg-[#333944]"
            >
              {allVisibleSelected ? 'Unselect all' : 'Select all'}
            </button>
            <button className="rounded-full border border-[#3a3f49] bg-[#2a2f37] px-3 py-2 text-sm text-gray-100 transition hover:bg-[#333944]">
              {selectedCount} selected
            </button>
            <button className="ml-auto rounded-full bg-[#3a3f49] p-3 text-gray-200 transition hover:bg-[#464d5a]" aria-label="Search sources">
              <Search className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-5">
        {displayedSources.length > 0 ? (
          <div className="space-y-3">
            {displayedSources.map((source) => (
              <div
                key={source.id}
                className={`rounded-2xl border p-4 transition-colors ${
                  selectedSourceIds.includes(source.id)
                    ? 'border-[#5563ff] bg-[#292e38] shadow-[0_0_0_1px_rgba(85,99,255,0.4)]'
                    : 'border-[#313641] bg-[#23272f]'
                }`}
              >
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => toggleSource(source.id)}
                    className="mt-1 rounded-md p-1 text-gray-300 transition hover:bg-[#313641] hover:text-white"
                    aria-label={selectedSourceIds.includes(source.id) ? `Unselect ${source.name}` : `Select ${source.name}`}
                  >
                    {selectedSourceIds.includes(source.id) ? <Check className="h-5 w-5" /> : <Square className="h-5 w-5" />}
                  </button>
                  <div className="mt-1 flex h-9 w-9 items-center justify-center rounded-lg bg-[#2e333c]">
                    <FileText className="h-4 w-4 text-gray-300" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-medium text-gray-100">{source.name}</p>
                    </div>
                    <p className="mt-1 text-xs text-gray-400">
                      {formatFileSize(source.size)} · {source.uploadedAt}
                    </p>
                    <p className="mt-2 text-xs text-gray-300">
                      {source.status === 'completed' ? 'Saved source' : 'Uploading source'}
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <button
                        onClick={() => openPreview(source)}
                        className="rounded-full border border-[#3a3f49] bg-[#2a2f37] px-3 py-1.5 text-xs font-medium text-gray-100 transition hover:bg-[#333944]"
                      >
                        Preview
                      </button>
                      <button
                        onClick={() => removeSource(source.id)}
                        className="rounded-full border border-[#3a3f49] bg-[#2a2f37] px-3 py-1.5 text-xs font-medium text-gray-100 transition hover:bg-[#333944] hover:text-red-200"
                        aria-label={`Remove ${source.name}`}
                      >
                        <span className="inline-flex items-center gap-1">
                          <Trash2 className="h-3.5 w-3.5" />
                          Remove
                        </span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center text-gray-400">
            <FilePlus2 className="h-10 w-10 text-gray-500" />
            <p className="mt-4 text-sm font-medium text-gray-300">Saved sources will appear here</p>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Click Add sources above to add PDFs, websites, text, videos, or audio files.
            </p>
          </div>
        )}
      </div>

    </aside>
  )
}

'use client'

import { useState } from 'react'
import { Upload, File, Trash2, CheckCircle, Clock } from 'lucide-react'

interface UploadedFile {
  id: string
  name: string
  size: number
  status: 'uploading' | 'completed' | 'failed'
  uploadedAt: string
}

const defaultUploadedFiles: UploadedFile[] = [
  {
    id: 'default-ael-earnings-presentation',
    name: 'AEL_Earnings_Presentation_Q2-FY26_copy.pdf',
    size: 2523226,
    status: 'completed',
    uploadedAt: 'Default document',
  },
]

export default function FileUploadSection() {
  const [files, setFiles] = useState<UploadedFile[]>(defaultUploadedFiles)
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)

    const droppedFiles = Array.from(e.dataTransfer.files)
    addFiles(droppedFiles)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files))
    }
  }

  const addFiles = (newFiles: File[]) => {
    const uploadedFiles = newFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      status: 'uploading' as const,
      uploadedAt: new Date().toLocaleString(),
    }))

    setFiles((prev) => [...prev, ...uploadedFiles])

    // Simulate upload completion
    uploadedFiles.forEach((file) => {
      setTimeout(() => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id ? { ...f, status: 'completed' } : f
          )
        )
      }, 2000)
    })
  }

  const deleteFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="flex-1 flex flex-col p-8 overflow-y-auto bg-[#f5efe4] dark:bg-[#0b1220] transition-colors">
      <div className="max-w-6xl mx-auto w-full">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Upload Documents</h1>
          <p className="text-gray-600 dark:text-blue-100/75">Upload your documents to build your knowledge base. Supported formats: PDF, TXT, DOCX</p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`mb-8 border-2 border-dashed rounded-lg p-12 transition-all text-center cursor-pointer ${
            isDragging
              ? 'border-[#bfa98b] dark:border-[#60a5fa] bg-[#fbf6ec] dark:bg-[#10192c] shadow-[0_0_0_1px_rgba(59,130,246,0.15)]'
              : 'border-[#d9cbbb] dark:border-[#22314f] hover:border-[#cdbb9f] dark:hover:border-[#60a5fa] hover:bg-[#fbf6ec] dark:hover:bg-[#10192c]'
          }`}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-[#bfa98b] dark:text-[#60a5fa] drop-shadow-[0_0_18px_rgba(59,130,246,0.18)]" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">Drag and drop your files here</h3>
          <p className="text-gray-600 dark:text-blue-100/65 mb-4">or</p>

          <label className="inline-block">
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              accept=".pdf,.txt,.docx"
            />
            <span className="px-6 py-2 bg-gradient-to-r from-[#f6c453] to-[#e5ae37] text-gray-900 dark:text-white rounded-lg font-medium hover:from-[#f8cd68] hover:to-[#eab843] dark:from-[#3b82f6] dark:to-[#2563eb] dark:hover:from-[#4f8cf7] dark:hover:to-[#1d4ed8] shadow-lg shadow-amber-500/25 dark:shadow-blue-500/25 transition-all inline-block cursor-pointer">
              Select Files
            </span>
          </label>

          <p className="text-sm text-gray-500 dark:text-blue-100/55 mt-4">Maximum file size: 50 MB</p>
        </div>

        {/* Files List */}
        {files.length > 0 && (
          <div className="bg-[#fbf6ec] dark:bg-[#0f172a] rounded-lg border border-[#e0d3c1] dark:border-[#22314f] p-6 shadow-sm dark:shadow-[0_8px_24px_rgba(2,6,23,0.22)]">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Uploaded Files ({files.length})
            </h2>

            <div className="space-y-3">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-4 bg-[#fffaf2] dark:bg-[#10192c] rounded-lg border border-[#e0d3c1] dark:border-[#22314f] hover:border-[#cdbb9f] dark:hover:border-[#60a5fa] transition-all group shadow-sm dark:shadow-[0_4px_14px_rgba(2,6,23,0.14)]"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <File className="w-5 h-5 text-gray-500 dark:text-[#60a5fa] flex-shrink-0" />

                    <div className="flex-1 min-w-0">
                      <p className="text-gray-900 dark:text-gray-100 font-medium truncate">{file.name}</p>
                      <div className="flex gap-4 text-sm text-gray-600 dark:text-blue-100/60 mt-1">
                        <span>{formatFileSize(file.size)}</span>
                        <span>{file.uploadedAt}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                    {file.status === 'uploading' && (
                      <div className="flex items-center gap-2 text-amber-700 dark:text-amber-300">
                        <Clock className="w-5 h-5 animate-spin" />
                        <span className="text-sm font-medium">Uploading</span>
                      </div>
                    )}

                    {file.status === 'completed' && (
                      <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
                        <CheckCircle className="w-5 h-5" />
                        <span className="text-sm font-medium">Completed</span>
                      </div>
                    )}

                    {file.status === 'failed' && (
                      <div className="flex items-center gap-2 text-red-700 dark:text-red-300">
                        <span className="text-sm font-medium">Failed</span>
                      </div>
                    )}

                    <button
                      onClick={() => deleteFile(file.id)}
                      className="p-2 text-gray-500 dark:text-blue-100/60 hover:text-red-700 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-[#241a2d] rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-[#f0e7d9] dark:bg-[#14213a] rounded-lg border border-[#e0d3c1] dark:border-[#24406e] shadow-sm">
              <p className="text-sm text-gray-600 dark:text-blue-100/70">
                <span className="font-semibold">{files.filter(f => f.status === 'completed').length}</span> of{' '}
                <span className="font-semibold">{files.length}</span> files indexed and ready for queries
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {files.length === 0 && (
          <div className="mt-12 p-8 bg-[#fbf6ec] dark:bg-[#10192c] rounded-lg border border-[#e0d3c1] dark:border-[#22314f] text-center shadow-sm dark:shadow-[0_8px_24px_rgba(2,6,23,0.22)]">
            <File className="w-12 h-12 mx-auto mb-4 text-gray-400 dark:text-[#60a5fa]" />
            <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-100 mb-2">No documents uploaded yet</h3>
            <p className="text-gray-600 dark:text-blue-100/70">Upload your first document to get started with PowerMind</p>
          </div>
        )}
      </div>
    </div>
  )
}

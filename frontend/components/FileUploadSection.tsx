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

export default function FileUploadSection() {
  const [files, setFiles] = useState<UploadedFile[]>([])
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
    <div className="flex-1 flex flex-col p-8 overflow-y-auto">
      <div className="max-w-6xl mx-auto w-full">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#f8fafc] mb-2">Upload Documents</h1>
          <p className="text-[#94a3b8]">Upload your documents to build your knowledge base. Supported formats: PDF, TXT, DOCX</p>
        </div>

        {/* Upload Area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`mb-8 border-2 border-dashed rounded-lg p-12 transition-all text-center cursor-pointer ${
            isDragging
              ? 'border-[#3b82f6] bg-[#3b82f6]/5'
              : 'border-[#334155] hover:border-[#475569] hover:bg-[#1e293b]/50'
          }`}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-[#3b82f6]" />
          <h3 className="text-lg font-semibold text-[#f8fafc] mb-1">Drag and drop your files here</h3>
          <p className="text-[#94a3b8] mb-4">or</p>
          
          <label className="inline-block">
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              className="hidden"
              accept=".pdf,.txt,.docx"
            />
            <span className="px-6 py-2 bg-[#3b82f6] text-white rounded-lg font-medium hover:bg-[#2563eb] transition-colors inline-block cursor-pointer">
              Select Files
            </span>
          </label>

          <p className="text-sm text-[#64748b] mt-4">Maximum file size: 50 MB</p>
        </div>

        {/* Files List */}
        {files.length > 0 && (
          <div className="bg-[#1e293b] rounded-lg border border-[#334155] p-6">
            <h2 className="text-lg font-semibold text-[#f8fafc] mb-4">
              Uploaded Files ({files.length})
            </h2>

            <div className="space-y-3">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-4 bg-[#0f172a] rounded-lg border border-[#334155] hover:border-[#475569] transition-colors group"
                >
                  <div className="flex items-center gap-4 flex-1 min-w-0">
                    <File className="w-5 h-5 text-[#94a3b8] flex-shrink-0" />
                    
                    <div className="flex-1 min-w-0">
                      <p className="text-[#f8fafc] font-medium truncate">{file.name}</p>
                      <div className="flex gap-4 text-sm text-[#64748b] mt-1">
                        <span>{formatFileSize(file.size)}</span>
                        <span>{file.uploadedAt}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 ml-4 flex-shrink-0">
                    {file.status === 'uploading' && (
                      <div className="flex items-center gap-2 text-[#f59e0b]">
                        <Clock className="w-5 h-5 animate-spin" />
                        <span className="text-sm font-medium">Uploading</span>
                      </div>
                    )}

                    {file.status === 'completed' && (
                      <div className="flex items-center gap-2 text-[#10b981]">
                        <CheckCircle className="w-5 h-5" />
                        <span className="text-sm font-medium">Completed</span>
                      </div>
                    )}

                    {file.status === 'failed' && (
                      <div className="flex items-center gap-2 text-[#ef4444]">
                        <span className="text-sm font-medium">Failed</span>
                      </div>
                    )}

                    <button
                      onClick={() => deleteFile(file.id)}
                      className="p-2 text-[#94a3b8] hover:text-[#ef4444] hover:bg-[#ef4444]/10 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-4 bg-[#334155]/30 rounded-lg border border-[#334155]">
              <p className="text-sm text-[#94a3b8]">
                <span className="font-semibold">{files.filter(f => f.status === 'completed').length}</span> of{' '}
                <span className="font-semibold">{files.length}</span> files indexed and ready for queries
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {files.length === 0 && (
          <div className="mt-12 p-8 bg-[#1e293b] rounded-lg border border-[#334155] text-center">
            <File className="w-12 h-12 mx-auto mb-4 text-[#475569]" />
            <h3 className="text-lg font-semibold text-[#cbd5e1] mb-2">No documents uploaded yet</h3>
            <p className="text-[#94a3b8]">Upload your first document to get started with PowerMind</p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * TypeScript type definitions for the application
 */

export interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export interface UploadedFile {
  id: string
  name: string
  size: number
  status: 'uploading' | 'completed' | 'failed'
  uploadedAt: string
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

export interface DocumentMetadata {
  id: string
  filename: string
  uploadedAt: Date
  size: number
  tokenCount?: number
  embeddingStatus: 'pending' | 'completed' | 'failed'
}

export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
  timestamp: string
}

export interface ChatRequest {
  message: string
  documentIds?: string[]
  context?: string
}

export interface ChatResponse {
  message: string
  sources: DocumentMetadata[]
  confidence?: number
  timestamp: string
}

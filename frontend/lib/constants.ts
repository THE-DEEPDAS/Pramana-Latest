/**
 * Application constants
 */

export const APP_CONFIG = {
  name: 'PowerMind',
  description: 'Retrieve and Generate intelligent responses with your documents',
  version: '0.1.0',
}

export const UPLOAD_CONFIG = {
  maxFileSize: 50 * 1024 * 1024, // 50 MB
  supportedFormats: ['.pdf', '.txt', '.docx'],
  maxFiles: 100,
}

export const CHAT_CONFIG = {
  maxMessageLength: 4000,
  typingDelayMs: 1500,
}

export const COLORS = {
  background: '#0f172a',
  card: '#1e293b',
  foreground: '#f8fafc',
  mutedText: '#94a3b8',
  border: '#334155',
  accentBlue: '#3b82f6',
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
}

export const MESSAGES = {
  welcome: 'Hello! I\'m PowerMind, your RAG assistant. Upload documents first, then ask me questions about them.',
  noDocuments: 'No documents uploaded yet. Upload your first document to get started.',
  uploadSuccess: 'File uploaded successfully!',
  uploadError: 'Failed to upload file. Please try again.',
  emptyChat: 'Start a conversation by asking a question.',
  loading: 'Thinking...',
}

export const ROUTES = {
  home: '/',
  chat: '#chat',
  upload: '#upload',
}

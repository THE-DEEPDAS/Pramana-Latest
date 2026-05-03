import { useState, useCallback } from 'react'

export interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  timestamp: Date
}

/**
 * Custom hook for managing chat messages
 */
export function useMessages(initialMessages: Message[] = []) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message])
  }, [])

  const addUserMessage = useCallback((content: string) => {
    const message: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date(),
    }
    addMessage(message)
    return message
  }, [addMessage])

  const addAssistantMessage = useCallback((content: string) => {
    const message: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content,
      timestamp: new Date(),
    }
    addMessage(message)
    return message
  }, [addMessage])

  const clearMessages = useCallback(() => {
    setMessages([])
  }, [])

  const deleteMessage = useCallback((id: string) => {
    setMessages((prev) => prev.filter((msg) => msg.id !== id))
  }, [])

  return {
    messages,
    addMessage,
    addUserMessage,
    addAssistantMessage,
    clearMessages,
    deleteMessage,
  }
}

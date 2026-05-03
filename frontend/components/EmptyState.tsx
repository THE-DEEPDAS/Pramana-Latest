import React from 'react'

interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="w-16 h-16 mb-4 text-gray-400 dark:text-[#475569]">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-700 dark:text-[#cbd5e1] mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-[#94a3b8] text-center max-w-md mb-6">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-amber-500 dark:bg-[#3b82f6] text-gray-900 dark:text-white rounded-lg font-medium hover:bg-amber-600 dark:hover:bg-[#2563eb] transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}

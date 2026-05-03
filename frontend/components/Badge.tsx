interface BadgeProps {
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info'
  children: React.ReactNode
}

const variantClasses = {
  default: 'bg-gray-200 dark:bg-[#334155] text-gray-800 dark:text-[#cbd5e1]',
  success: 'bg-green-100 dark:bg-[#10b981]/20 text-green-700 dark:text-[#10b981] border border-green-300 dark:border-[#10b981]/50',
  error: 'bg-red-100 dark:bg-[#ef4444]/20 text-red-700 dark:text-[#ef4444] border border-red-300 dark:border-[#ef4444]/50',
  warning: 'bg-amber-100 dark:bg-[#f59e0b]/20 text-amber-700 dark:text-[#f59e0b] border border-amber-300 dark:border-[#f59e0b]/50',
  info: 'bg-amber-100 dark:bg-[#3b82f6]/20 text-amber-800 dark:text-[#3b82f6] border border-amber-300 dark:border-[#3b82f6]/50',
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${variantClasses[variant]}`}>
      {children}
    </span>
  )
}

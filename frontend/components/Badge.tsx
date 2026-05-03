interface BadgeProps {
  variant?: 'default' | 'success' | 'error' | 'warning' | 'info'
  children: React.ReactNode
}

const variantClasses = {
  default: 'bg-[#334155] text-[#cbd5e1]',
  success: 'bg-[#10b981]/20 text-[#10b981] border border-[#10b981]/50',
  error: 'bg-[#ef4444]/20 text-[#ef4444] border border-[#ef4444]/50',
  warning: 'bg-[#f59e0b]/20 text-[#f59e0b] border border-[#f59e0b]/50',
  info: 'bg-[#3b82f6]/20 text-[#3b82f6] border border-[#3b82f6]/50',
}

export function Badge({ variant = 'default', children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${variantClasses[variant]}`}>
      {children}
    </span>
  )
}

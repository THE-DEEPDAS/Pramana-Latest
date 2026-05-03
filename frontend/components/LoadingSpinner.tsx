export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

export function LoadingSpinner({ size = 'md', text }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`${sizeClasses[size]} border-2 border-[#334155] border-t-[#3b82f6] rounded-full animate-spin`} />
      {text && <p className="text-sm text-[#94a3b8]">{text}</p>}
    </div>
  )
}

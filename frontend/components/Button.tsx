import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: React.ReactNode
}

const variantClasses = {
  primary:
    'bg-[#3b82f6] text-white hover:bg-[#2563eb] disabled:bg-[#475569] disabled:cursor-not-allowed',
  secondary:
    'bg-[#334155] text-[#f8fafc] hover:bg-[#475569] disabled:opacity-50 disabled:cursor-not-allowed',
  outline:
    'border border-[#334155] text-[#cbd5e1] hover:border-[#475569] hover:bg-[#1e293b]/50 disabled:opacity-50 disabled:cursor-not-allowed',
  ghost:
    'text-[#cbd5e1] hover:bg-[#1e293b] disabled:opacity-50 disabled:cursor-not-allowed',
  danger:
    'bg-[#ef4444] text-white hover:bg-[#dc2626] disabled:bg-[#475569] disabled:cursor-not-allowed',
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading,
      disabled,
      className,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={`inline-flex items-center gap-2 rounded-lg font-medium transition-colors ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

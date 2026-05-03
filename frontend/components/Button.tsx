import React from 'react'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  children: React.ReactNode
}

const variantClasses = {
  primary:
    'bg-gradient-to-r from-[#f6c453] to-[#e5ae37] dark:from-[#2563eb] dark:to-[#1d4ed8] text-gray-900 dark:text-white hover:from-[#f8cd68] hover:to-[#eab843] dark:hover:from-[#3b82f6] dark:hover:to-[#2563eb] shadow-lg shadow-amber-500/25 dark:shadow-blue-500/25 hover:shadow-amber-500/35 dark:hover:shadow-blue-500/35 disabled:bg-gray-400 dark:disabled:bg-[#475569] disabled:cursor-not-allowed',
  secondary:
    'bg-white/80 dark:bg-[#13213f] text-gray-900 dark:text-blue-50 border border-[#e6d8b4] dark:border-[#24406e] hover:bg-[#fff4dc] dark:hover:bg-[#173059] shadow-sm dark:shadow-[0_4px_14px_rgba(37,99,235,0.12)] disabled:opacity-50 disabled:cursor-not-allowed',
  outline:
    'border border-gray-300 dark:border-[#24406e] text-gray-700 dark:text-blue-100 hover:border-gray-400 dark:hover:border-[#60a5fa] hover:bg-gray-50 dark:hover:bg-[#14213a] disabled:opacity-50 disabled:cursor-not-allowed',
  ghost:
    'text-gray-700 dark:text-blue-100 hover:bg-gray-100 dark:hover:bg-[#14213a] disabled:opacity-50 disabled:cursor-not-allowed',
  danger:
    'bg-red-600 dark:bg-[#ef4444] text-white hover:bg-red-700 dark:hover:bg-[#dc2626] disabled:bg-gray-400 dark:disabled:bg-[#475569] disabled:cursor-not-allowed',
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
        className={`inline-flex items-center gap-2 rounded-lg font-medium transition-all ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
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

interface CardProps {
  children: React.ReactNode
  className?: string
}

export function Card({ children, className = '' }: CardProps) {
  return (
    <div className={`bg-gray-50 dark:bg-[#0f172a] rounded-lg border border-gray-200 dark:border-[#22314f] shadow-sm dark:shadow-[0_8px_24px_rgba(2,6,23,0.22)] ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: CardProps) {
  return (
    <div className={`px-6 py-4 border-b border-gray-200 dark:border-[#22314f] ${className}`}>
      {children}
    </div>
  )
}

export function CardBody({ children, className = '' }: CardProps) {
  return (
    <div className={`px-6 py-4 ${className}`}>
      {children}
    </div>
  )
}

export function CardFooter({ children, className = '' }: CardProps) {
  return (
    <div className={`px-6 py-4 border-t border-gray-200 dark:border-[#22314f] ${className}`}>
      {children}
    </div>
  )
}

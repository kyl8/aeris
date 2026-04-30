import { cn } from '../../lib/cn'

const variantClasses = {
  primary: 'border border-zinc-100 bg-zinc-100 text-zinc-950 hover:bg-white',
  secondary: 'border border-zinc-800 bg-transparent text-zinc-100 hover:border-zinc-600 hover:bg-zinc-900',
}

export function ActionLink({ variant = 'primary', className = '', children, ...props }) {
  return (
    <a
      className={cn(
        'inline-flex items-center justify-center rounded-full px-5 py-2.5 text-sm font-medium transition-colors',
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </a>
  )
}
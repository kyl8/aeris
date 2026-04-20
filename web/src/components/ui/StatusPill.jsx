import { cn } from '../../lib/cn'

const toneClasses = {
  success: 'border-zinc-300/25 bg-zinc-100/5 text-zinc-100',
  warning: 'border-zinc-500/25 bg-zinc-100/5 text-zinc-200',
  danger: 'border-zinc-500/40 bg-zinc-100/5 text-zinc-100',
  neutral: 'border-zinc-800 bg-zinc-900 text-zinc-300',
}

export function StatusPill({ tone = 'neutral', className = '', children }) {
  return (
    <span
      className={cn(
        'inline-flex w-fit items-center rounded-full border px-3 py-1 text-[0.7rem] font-semibold uppercase tracking-[0.24em]',
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}
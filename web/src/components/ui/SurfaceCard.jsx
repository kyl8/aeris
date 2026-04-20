import { cn } from '../../lib/cn'

export function SurfaceCard({ className = '', children }) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-zinc-800 bg-zinc-950',
        className,
      )}
    >
      {children}
    </div>
  )
}
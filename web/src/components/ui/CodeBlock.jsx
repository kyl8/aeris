import { cn } from '../../lib/cn'

export function CodeBlock({ title, children, className = '' }) {
  return (
    <div className={cn('overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950', className)}>
      {title ? (
        <div className="border-b border-zinc-800 px-4 py-3 text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
          {title}
        </div>
      ) : null}
      <pre className="overflow-auto px-4 py-4 text-sm leading-6 text-zinc-200">
        <code>{children}</code>
      </pre>
    </div>
  )
}

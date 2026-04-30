import { cn } from '../../lib/cn'

export function SectionHeading({ eyebrow, title, description, className = '' }) {
  return (
    <div className={cn('flex flex-col gap-3 scroll-mt-24', className)}>
      {eyebrow ? (
        <p className="w-fit text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-zinc-500">
          {eyebrow}
        </p>
      ) : null}

      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-zinc-100 sm:text-3xl">{title}</h2>
        {description ? (
          <p className="max-w-3xl text-sm leading-6 text-zinc-400 sm:text-base">{description}</p>
        ) : null}
      </div>
    </div>
  )
}
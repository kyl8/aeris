import { useTranslation } from 'react-i18next'

import { StatusPill } from '../ui/StatusPill'

export function DocsSidebar({ items, health, isLoading }) {
  const { t } = useTranslation()
  const statusTone = isLoading ? 'neutral' : health.status === 'offline' ? 'danger' : 'success'
  const statusLabel = isLoading
    ? t('health.loading')
    : t(`health.status.${health.status}`, { defaultValue: health.status })

  return (
    <aside className="hidden border-r border-zinc-800 lg:block">
      <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-auto px-4 py-8 sm:px-6 lg:px-8">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
          {t('sidebar.title')}
        </p>

        <nav className="mt-4 space-y-1">
          {items.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="block rounded-lg px-3 py-2 text-sm text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
            >
              {t(item.labelKey)}
            </a>
          ))}
        </nav>

        <div className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-950 p-4">
          <StatusPill tone={statusTone}>{statusLabel}</StatusPill>
          <p className="mt-3 text-sm leading-6 text-zinc-400">
            {health.service} v{health.version}
          </p>
          <p className="mt-2 text-xs uppercase tracking-[0.24em] text-zinc-500">{t('sidebar.preview')}</p>
        </div>
      </div>
    </aside>
  )
}

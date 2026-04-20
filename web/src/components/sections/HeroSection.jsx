import { useTranslation } from 'react-i18next'

import { ActionLink } from '../ui/ActionLink'
import { StatusPill } from '../ui/StatusPill'

function getHealthTone(status, isLoading) {
  if (isLoading) {
    return 'warning'
  }

  return status === 'offline' ? 'danger' : 'success'
}

export function HeroSection({ health, isHealthLoading, docsUrl, redocUrl }) {
  const { t } = useTranslation()
  const statusLabel = isHealthLoading
    ? t('health.loading')
    : t(`health.status.${health.status}`, { defaultValue: health.status })

  return (
    <section id="overview" className="scroll-mt-24 border-b border-zinc-800 pb-10">
      <div className="max-w-3xl space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <StatusPill tone={getHealthTone(health.status, isHealthLoading)}>{t('hero.badge')}</StatusPill>
          <span className="text-sm text-zinc-500">
            {health.service} v{health.version}
          </span>
        </div>

        <div className="space-y-4">
          <h1 className="text-4xl font-semibold tracking-tight text-zinc-100 sm:text-5xl lg:text-6xl">
            {t('hero.title')}
          </h1>
          <p className="max-w-2xl text-base leading-7 text-zinc-400 sm:text-lg">
            {t('hero.description')}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <ActionLink href="#getting-started" variant="secondary">
            {t('hero.getStarted')}
          </ActionLink>
          <ActionLink href={docsUrl} target="_blank" rel="noreferrer" variant="secondary">
            {t('hero.openSwagger')}
          </ActionLink>
          <ActionLink href={redocUrl} target="_blank" rel="noreferrer" variant="secondary">
            {t('hero.viewRedoc')}
          </ActionLink>
        </div>

        <p className="text-sm uppercase tracking-[0.24em] text-zinc-500">{t('hero.apiStatus', { status: statusLabel })}</p>
      </div>
    </section>
  )
}
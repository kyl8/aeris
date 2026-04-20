import { useTranslation } from 'react-i18next'

import { StatusPill } from './StatusPill'

function ResultRow({ label, value }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3">
      <p className="text-[0.72rem] uppercase tracking-[0.22em] text-zinc-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-zinc-100">{value}</p>
    </div>
  )
}

export function ResultPanel({ prediction }) {
  const { t } = useTranslation()

  if (!prediction) {
    return (
      <div className="flex min-h-[20rem] flex-col justify-between rounded-2xl border border-zinc-800 bg-zinc-950 p-5 sm:p-6">
        <div className="space-y-3">
          <StatusPill tone="neutral">{t('result.title')}</StatusPill>
          <h3 className="text-lg font-semibold text-zinc-100">
            {t('result.emptyTitle')}
          </h3>
          <p className="text-sm leading-6 text-zinc-400">
            {t('result.emptyDescription')}
          </p>
        </div>

        <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-500">
          {t('result.emptyState')}
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[20rem] flex-col gap-4 rounded-2xl border border-zinc-800 bg-zinc-950 p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3">
        <StatusPill tone="success">{t('result.title')}</StatusPill>
        <span className="text-xs uppercase tracking-[0.22em] text-zinc-500">
          {prediction.feature_count} {t('result.features')}
        </span>
      </div>

      <div className="grid gap-3">
        <ResultRow label={t('result.model')} value={prediction.model_name} />
        <ResultRow label={t('result.version')} value={prediction.model_version} />
        <ResultRow label={t('result.prediction')} value={prediction.prediction} />
        <ResultRow
          label={t('result.artifact')}
          value={prediction.artifact_path ?? t('result.placeholderArtifact')}
        />
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-4">
        <p className="text-[0.72rem] uppercase tracking-[0.22em] text-zinc-500">{t('result.normalized')}</p>
        <pre className="mt-3 overflow-auto text-sm leading-6 text-zinc-200">
          {JSON.stringify(prediction.normalized_features, null, 2)}
        </pre>
      </div>

      <p className="text-sm leading-6 text-zinc-400">{prediction.detail}</p>
    </div>
  )
}

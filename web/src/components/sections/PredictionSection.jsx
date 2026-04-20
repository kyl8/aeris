import { useTranslation } from 'react-i18next'

import { SectionHeading } from '../layout/SectionHeading'
import { ResultPanel } from '../ui/ResultPanel'
import { SurfaceCard } from '../ui/SurfaceCard'
import { usePrediction } from '../../hooks/usePrediction'

export function PredictionSection() {
  const { t } = useTranslation()
  const {
    featuresInput,
    setFeaturesInput,
    parsedFeatures,
    prediction,
    error,
    isSubmitting,
    submit,
  } = usePrediction()

  return (
    <section id="playground" className="scroll-mt-24 pb-10">
      <SectionHeading
        eyebrow={t('sections.playground.eyebrow')}
        title={t('sections.playground.title')}
        description={t('sections.playground.description')}
      />

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <SurfaceCard className="p-5 sm:p-6">
          <form className="space-y-4" onSubmit={submit}>
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
                {t('sections.playground.endpointLabel')}
              </p>
              <label htmlFor="features" className="text-sm font-medium text-zinc-100">
                {t('sections.playground.fieldLabel')}
              </label>
            </div>

            <textarea
              id="features"
              value={featuresInput}
              onChange={(event) => setFeaturesInput(event.target.value)}
              placeholder={t('sections.playground.placeholder')}
              className="min-h-44 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-4 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-zinc-500"
            />

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center rounded-full border border-zinc-100 bg-zinc-100 px-4 py-2.5 text-sm font-medium text-zinc-950 transition-colors hover:bg-white disabled:cursor-wait disabled:opacity-70"
              >
                {isSubmitting ? t('sections.playground.running') : t('sections.playground.submit')}
              </button>

              <span className="text-sm text-zinc-500">
                {t('sections.playground.valuesDetected', { count: parsedFeatures.length })}
              </span>
            </div>

            {error ? <p className="text-sm leading-6 text-zinc-400">{error}</p> : null}
          </form>
        </SurfaceCard>

        <ResultPanel prediction={prediction} />
      </div>
    </section>
  )
}
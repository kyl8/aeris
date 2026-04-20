import { useTranslation } from 'react-i18next'

import { SectionHeading } from '../layout/SectionHeading'

export function EndpointSection({ endpoints }) {
  const { t } = useTranslation()

  return (
    <section id="api-reference" className="scroll-mt-24 border-b border-zinc-800 pb-10">
      <SectionHeading
        eyebrow={t('sections.apiReference.eyebrow')}
        title={t('sections.apiReference.title')}
        description={t('sections.apiReference.description')}
      />

      <div className="mt-6 overflow-hidden rounded-2xl border border-zinc-800">
        {endpoints.map((endpoint, index) => (
          <div
            key={endpoint.path}
            className={`grid gap-4 px-4 py-4 sm:grid-cols-[120px_220px_minmax(0,1fr)] ${
              index !== endpoints.length - 1 ? 'border-b border-zinc-800' : ''
            }`}
          >
            <span className="font-mono text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
              {endpoint.method}
            </span>
            <code className="font-mono text-sm text-zinc-100">{endpoint.path}</code>
            <p className="text-sm leading-6 text-zinc-400">{t(endpoint.descriptionKey)}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
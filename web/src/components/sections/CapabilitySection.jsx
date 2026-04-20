import { useTranslation } from 'react-i18next'

import { SectionHeading } from '../layout/SectionHeading'
import { CodeBlock } from '../ui/CodeBlock'
import { quickStartCommands, projectTree, structureNotes } from '../../data/landingContent'

export function CapabilitySection() {
  const { t } = useTranslation()

  return (
    <section id="getting-started" className="scroll-mt-24 border-b border-zinc-800 pb-10">
      <SectionHeading
        eyebrow={t('sections.gettingStarted.eyebrow')}
        title={t('sections.gettingStarted.title')}
        description={t('sections.gettingStarted.description')}
      />

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {quickStartCommands.map((item) => (
          <CodeBlock key={item.titleKey} title={t(item.titleKey)}>
            {t(item.commandKey)}
          </CodeBlock>
        ))}
      </div>

      <section id="structure" className="mt-10 scroll-mt-24">
        <SectionHeading
          eyebrow={t('sections.structure.eyebrow')}
          title={t('sections.structure.title')}
          description={t('sections.structure.description')}
        />

        <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
          <CodeBlock title={t('sections.structure.treeTitle')}>{projectTree}</CodeBlock>

          <div className="rounded-2xl border border-zinc-800 bg-zinc-950 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-zinc-500">
              {t('sections.structure.notesTitle')}
            </p>

            <ul className="mt-4 space-y-4 text-sm leading-6 text-zinc-400">
              {structureNotes.map((item) => (
                <li key={item.titleKey}>
                  <p className="font-medium text-zinc-100">{t(item.titleKey)}</p>
                  <p className="mt-1">{t(item.textKey)}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </section>
  )
}
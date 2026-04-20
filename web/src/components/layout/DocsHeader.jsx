import { useTranslation } from 'react-i18next'

import { ActionLink } from '../ui/ActionLink'
import { LanguageSwitcher } from './LanguageSwitcher'

export function DocsHeader({ links, navItems }) {
  const { t } = useTranslation()

  return (
    <header className="sticky top-0 z-30 border-b border-zinc-800 bg-zinc-950">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center gap-4 px-4 sm:px-6 lg:px-8">
        <a
          href="#overview"
          className="flex items-center gap-2 text-sm font-semibold tracking-wide text-zinc-100"
        >
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 text-sm">
            A
          </span>
          {t('header.brand')}
        </a>

        <nav className="hidden items-center gap-6 text-sm text-zinc-400 md:flex">
          {navItems.map((item) => (
            <a key={item.href} className="transition-colors hover:text-zinc-100" href={item.href}>
              {t(item.labelKey)}
            </a>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden items-center gap-2 rounded-xl border border-zinc-800 px-3 py-2 text-sm text-zinc-500 lg:flex">
            <span>{t('header.search')}</span>
            <kbd className="rounded border border-zinc-700 px-1.5 py-0.5 text-[0.7rem] text-zinc-400">
              Ctrl K
            </kbd>
          </div>

          <LanguageSwitcher />

          <ActionLink variant="secondary" href={links.swagger} target="_blank" rel="noreferrer">
            {t('header.openApi')}
          </ActionLink>
        </div>
      </div>
    </header>
  )
}

import { useTranslation } from 'react-i18next'

const languageOptions = [
  { value: 'pt-BR', labelKey: 'header.language.options.ptBR' },
  { value: 'en-US', labelKey: 'header.language.options.enUS' },
]

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation()
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language ?? 'pt-BR'

  async function handleChange(event) {
    await i18n.changeLanguage(event.target.value)
  }

  return (
    <label className="inline-flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-400">
      <span className="sr-only">{t('header.language.label')}</span>
      <select
        value={currentLanguage}
        onChange={handleChange}
        aria-label={t('header.language.label')}
        className="cursor-pointer bg-transparent text-sm text-zinc-100 outline-none"
      >
        {languageOptions.map((option) => (
          <option key={option.value} value={option.value} className="bg-zinc-950 text-zinc-100">
            {t(option.labelKey)}
          </option>
        ))}
      </select>
    </label>
  )
}
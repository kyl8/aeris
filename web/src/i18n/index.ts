import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import enUS from './resources/en-US'
import ptBR from './resources/pt-BR'

const supportedLanguages = ['pt-BR', 'en-US']

function getInitialLanguage() {
  if (typeof window === 'undefined') {
    return 'pt-BR'
  }

  const storedLanguage = window.localStorage.getItem('aeris-language')
  if (storedLanguage && supportedLanguages.includes(storedLanguage)) {
    return storedLanguage
  }

  const browserLanguage = window.navigator.language?.toLowerCase() ?? ''
  if (browserLanguage.startsWith('en')) {
    return 'en-US'
  }

  return 'pt-BR'
}

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources: {
      'pt-BR': ptBR,
      'en-US': enUS,
    },
    lng: getInitialLanguage(),
    fallbackLng: 'pt-BR',
    supportedLngs: supportedLanguages,
    interpolation: {
      escapeValue: false,
    },
  })

  if (typeof window !== 'undefined') {
    i18n.on('languageChanged', (language) => {
      if (supportedLanguages.includes(language)) {
        window.localStorage.setItem('aeris-language', language)
      }
    })
  }
}

export default i18n
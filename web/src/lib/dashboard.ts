import i18n from '../i18n'

const climateClassTranslations = {
  'cloudy/overcast': 'classes.cloudyOvercast',
  'foggy/hazy': 'classes.foggyHazy',
  'rain/storm': 'classes.rainStorm',
  'rain/strom': 'classes.rainStorm',
  'snow/frosty': 'classes.snowFrosty',
  'sun/clear': 'classes.sunClear',
  ceu_limpo: 'classes.sunClear',
  chuva: 'classes.rainStorm',
  neblina: 'classes.foggyHazy',
  nublado: 'classes.cloudyOvercast',
  tempestade: 'classes.rainStorm',
  dew: 'classes.dew',
  fogsmog: 'classes.fogsmog',
  frost: 'classes.frost',
  glaze: 'classes.glaze',
  hail: 'classes.hail',
  lightning: 'classes.lightning',
  rain: 'classes.rain',
  rainbow: 'classes.rainbow',
  rime: 'classes.rime',
  sandstorm: 'classes.sandstorm',
  snow: 'classes.snow',
}

export function formatConfidence(value) {
  if (!Number.isFinite(value)) {
    return '0%'
  }

  return `${Math.round(value * 100)}%`
}

export function formatDateTime(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatDateLabel(value) {
  if (!value) {
    return 'Sem data'
  }

  return new Intl.DateTimeFormat('pt-BR', {
    month: 'short',
    day: '2-digit',
  }).format(new Date(`${value}T00:00:00`))
}

export function capitalizeLabel(value) {
  if (!value) {
    return 'Indefinido'
  }

  const normalizedValue = value.toString().trim().toLowerCase()
  const translationKey = climateClassTranslations[normalizedValue]

  if (translationKey) {
    const translatedValue = i18n.t(translationKey, { defaultValue: '' })
    if (translatedValue) {
      return translatedValue
    }
  }

  return value
    .toString()
    .replaceAll('_', ' ')
    .replace(/\b\p{L}/gu, (character) => character.toUpperCase())
}

export function summarizeHistory(historyItems) {
  const total = historyItems.length
  const averageConfidence = total
    ? historyItems.reduce((accumulator, item) => accumulator + (item.confidence ?? 0), 0) / total
    : 0

  const classCounts = new Map()
  let latestItem = null

  for (const item of historyItems) {
    const className = item.class ?? 'indefinido'
    classCounts.set(className, (classCounts.get(className) ?? 0) + 1)

    if (!latestItem) {
      latestItem = item
      continue
    }

    if (new Date(item.created_at) > new Date(latestItem.created_at)) {
      latestItem = item
    }
  }

  const topClassEntry = [...classCounts.entries()].sort((left, right) => right[1] - left[1])[0] ?? null

  return {
    total,
    averageConfidence,
    uniqueClasses: classCounts.size,
    topClass: topClassEntry ? topClassEntry[0] : 'indefinido',
    latestItem,
  }
}

export function buildDistributionData(historyItems) {
  const counts = new Map()

  for (const item of historyItems) {
    const className = item.class ?? 'indefinido'
    counts.set(className, (counts.get(className) ?? 0) + 1)
  }

  return [...counts.entries()]
    .map(([className, count]) => ({
      name: capitalizeLabel(className),
      value: count,
      rawName: className,
    }))
    .sort((left, right) => right.value - left.value)
}

export function buildTimelineData(historyItems) {
  const counts = new Map()

  for (const item of historyItems) {
    const timestamp = item.created_at ? new Date(item.created_at) : null
    if (!timestamp || Number.isNaN(timestamp.getTime())) {
      continue
    }

    const key = timestamp.toISOString().slice(0, 10)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }

  return [...counts.entries()]
    .sort((left, right) => left[0].localeCompare(right[0]))
    .map(([dateKey, count]) => ({
      date: dateKey,
      label: formatDateLabel(dateKey),
      count,
    }))
}

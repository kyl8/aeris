const DEFAULT_API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'
const API_BASE_URL = DEFAULT_API_URL.replace(/\/$/, '')

function buildUrl(path) {
  return `${API_BASE_URL}${path}`
}

async function readJsonResponse(response) {
  const contentType = response.headers.get('content-type') ?? ''

  if (!response.ok) {
    if (contentType.includes('application/json')) {
      const payload = await response.json()
      throw new Error(payload.error ?? payload.detail ?? 'A requisição falhou.')
    }

    throw new Error('A requisição falhou.')
  }

  if (!contentType.includes('application/json')) {
    return null
  }

  return response.json()
}

export function getDocsUrl(path) {
  return buildUrl(path)
}

export async function fetchHealth() {
  const response = await fetch(buildUrl('/api/v1/health'))
  return readJsonResponse(response)
}

export async function fetchHistory({ date, climateClass } = {}) {
  const params = new URLSearchParams()

  if (date) {
    params.set('date', date)
  }

  if (climateClass) {
    params.set('class', climateClass)
  }

  const query = params.toString()
  const response = await fetch(buildUrl(`/api/v1/history${query ? `?${query}` : ''}`))
  return readJsonResponse(response)
}

export async function predictClimate({ file, imageBase64 } = {}) {
  const formData = new FormData()

  if (file) {
    formData.append('image', file, file.name || 'image.png')
  }

  if (imageBase64) {
    formData.append('image_base64', imageBase64)
  }

  const response = await fetch(buildUrl('/api/v1/predict'), {
    method: 'POST',
    body: formData,
  })

  return readJsonResponse(response)
}

export const docsUrls = {
  swagger: getDocsUrl('/docs'),
  redoc: getDocsUrl('/redoc'),
  redocs: getDocsUrl('/redocs'),
}
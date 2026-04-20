const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

function buildUrl(path) {
  return `${API_BASE_URL}${path}`
}

async function readJsonResponse(response) {
  const contentType = response.headers.get('content-type') ?? ''

  if (!response.ok) {
    if (contentType.includes('application/json')) {
      const payload = await response.json()
      throw new Error(payload.detail ?? 'A requisição falhou.')
    }

    throw new Error('A requisição falhou.')
  }

  if (!contentType.includes('application/json')) {
    return null
  }

  return response.json()
}

export async function fetchHealth() {
  const response = await fetch(buildUrl('/health'))
  return readJsonResponse(response)
}

export async function predictFeatures(features) {
  const response = await fetch(buildUrl('/api/predict'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ features }),
  })

  return readJsonResponse(response)
}
import { useEffect, useState } from 'react'
import { fetchHealth } from '../lib/api'

const loadingHealth = {
  status: 'checando...',
  service: 'Aeris API',
  version: '0.1.0',
}

const fallbackHealth = {
  status: 'offline',
  service: 'Aeris API',
  version: '0.1.0',
}

export function useHealth() {
  const [health, setHealth] = useState(loadingHealth)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isActive = true

    async function loadHealth() {
      try {
        const data = await fetchHealth()
        if (isActive) {
          setHealth(data)
        }
      } catch {
        if (isActive) {
          setHealth(fallbackHealth)
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    loadHealth()

    return () => {
      isActive = false
    }
  }, [])

  return {
    health,
    isLoading,
  }
}
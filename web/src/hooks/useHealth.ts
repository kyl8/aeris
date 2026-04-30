import { useEffect, useState } from 'react'

import { fetchHealth } from '../lib/api'

const loadingHealth = {
  status: 'checando...',
}

const fallbackHealth = {
  status: 'offline',
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
    isHealthy: !isLoading && health.status === 'online',
  }
}
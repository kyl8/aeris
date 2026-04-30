import { useEffect, useState } from 'react'

import { fetchHistory } from '../lib/api'

const defaultFilters = {
  date: '',
  climateClass: '',
}

export function useHistory() {
  const [filters, setFilters] = useState(defaultFilters)
  const [history, setHistory] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshIndex, setRefreshIndex] = useState(0)

  useEffect(() => {
    let isActive = true

    async function loadHistory() {
      setIsLoading(true)
      setError('')

      try {
        const data = await fetchHistory({
          date: filters.date || undefined,
          climateClass: filters.climateClass || undefined,
        })

        if (isActive) {
          setHistory(data.items ?? [])
        }
      } catch (requestError) {
        if (isActive) {
          setHistory([])
          setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar o histórico.')
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    loadHistory()

    return () => {
      isActive = false
    }
  }, [filters.climateClass, filters.date, refreshIndex])

  function refresh() {
    setRefreshIndex((currentValue) => currentValue + 1)
  }

  function setFilter(field, value) {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [field]: value,
    }))
  }

  return {
    history,
    isLoading,
    error,
    filters,
    setFilter,
    refresh,
  }
}
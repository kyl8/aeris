import { useEffect, useMemo, useState } from 'react'

import {
  analyzeClimate,
  analyzeBaixadaSantista,
  clearResearchJob,
  fetchResearchStatus,
  startClimateDatasetBuild,
  startSatelliteDownload,
} from '../lib/api'

const emptyStatus = {
  historical_eval_dir: '',
  image_count: 0,
  latest_image: null,
  climate_dataset_path: '',
  climate_dataset_exists: false,
  climate_dataset_rows: 0,
  baixada_report_path: '',
  baixada_report_exists: false,
  baixada_report_updated_at: null,
  cdse_credentials_configured: false,
  jobs: [],
}

export function useResearch() {
  const [status, setStatus] = useState(emptyStatus)
  const [isLoading, setIsLoading] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [isAnalyzingClimate, setIsAnalyzingClimate] = useState(false)
  const [isAnalyzingBaixada, setIsAnalyzingBaixada] = useState(false)
  const [climateResult, setClimateResult] = useState<Record<string, any> | null>(null)
  const [baixadaResult, setBaixadaResult] = useState<Record<string, any> | null>(null)
  const [error, setError] = useState('')
  const [refreshIndex, setRefreshIndex] = useState(0)

  const hasRunningJob = useMemo(
    () => status.jobs.some((job) => job.status === 'running'),
    [status.jobs],
  )

  useEffect(() => {
    let isActive = true

    async function loadStatus() {
      setError('')
      try {
        const data = await fetchResearchStatus()
        if (isActive) {
          setStatus(data)
        }
      } catch (requestError) {
        if (isActive) {
          setError(requestError instanceof Error ? requestError.message : 'Falha ao carregar o status de pesquisa.')
        }
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    loadStatus()

    return () => {
      isActive = false
    }
  }, [refreshIndex])

  useEffect(() => {
    if (!hasRunningJob) {
      return undefined
    }

    const intervalId = window.setInterval(() => {
      setRefreshIndex((currentValue) => currentValue + 1)
    }, 4000)

    return () => window.clearInterval(intervalId)
  }, [hasRunningJob])

  function refresh() {
    setIsLoading(true)
    setRefreshIndex((currentValue) => currentValue + 1)
  }

  async function runSatelliteDownload(payload) {
    setIsStarting(true)
    setError('')
    try {
      await startSatelliteDownload(payload)
      refresh()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao iniciar download Sentinel-2.')
    } finally {
      setIsStarting(false)
    }
  }

  async function runClimateDatasetBuild(payload) {
    setIsStarting(true)
    setError('')
    try {
      await startClimateDatasetBuild(payload)
      refresh()
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao iniciar pipeline multimodal.')
    } finally {
      setIsStarting(false)
    }
  }

  async function clearJob(jobKey) {
    setIsStarting(true)
    setError('')
    try {
      const data = await clearResearchJob(jobKey)
      setStatus(data)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao limpar job de pesquisa.')
    } finally {
      setIsStarting(false)
    }
  }

  async function runClimateAnalysis(payload = {}) {
    setIsAnalyzingClimate(true)
    setError('')
    try {
      const data = await analyzeClimate(payload)
      setClimateResult(data.result)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao analisar sinal climatico.')
    } finally {
      setIsAnalyzingClimate(false)
    }
  }

  async function runBaixadaAnalysis(payload = {}) {
    setIsAnalyzingBaixada(true)
    setError('')
    try {
      const data = await analyzeBaixadaSantista(payload)
      setBaixadaResult(data.result)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Falha ao analisar a Baixada Santista.')
    } finally {
      setIsAnalyzingBaixada(false)
    }
  }

  return {
    status,
    isLoading,
    isStarting,
    isAnalyzingClimate,
    isAnalyzingBaixada,
    climateResult,
    baixadaResult,
    hasRunningJob,
    error,
    refresh,
    runSatelliteDownload,
    runClimateDatasetBuild,
    clearJob,
    runClimateAnalysis,
    runBaixadaAnalysis,
  }
}

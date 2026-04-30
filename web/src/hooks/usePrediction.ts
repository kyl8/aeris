import { useEffect, useRef, useState } from 'react'

import { predictClimate } from '../lib/api'

const defaultErrorMessage = 'Selecione uma imagem para enviar.'

export function usePrediction(onSuccess) {
  const [mode, setModeState] = useState('upload')
  const [selectedFile, setSelectedFileState] = useState(null)
  const [base64Input, setBase64InputState] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')
  const [prediction, setPrediction] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const currentObjectUrlRef = useRef('')

  useEffect(() => {
    return () => {
      if (currentObjectUrlRef.current) {
        URL.revokeObjectURL(currentObjectUrlRef.current)
        currentObjectUrlRef.current = ''
      }
    }
  }, [])

  function clearObjectUrl() {
    if (currentObjectUrlRef.current) {
      URL.revokeObjectURL(currentObjectUrlRef.current)
      currentObjectUrlRef.current = ''
    }
  }

  function setSelectedFile(file) {
    setSelectedFileState(file)

    clearObjectUrl()

    if (file) {
      const objectUrl = URL.createObjectURL(file)
      currentObjectUrlRef.current = objectUrl
      setPreviewUrl(objectUrl)
      return
    }

    setPreviewUrl('')
  }

  function setBase64Input(value) {
    setBase64InputState(value)

    clearObjectUrl()

    const rawValue = value.trim()
    if (!rawValue) {
      setPreviewUrl('')
      return
    }

    setPreviewUrl(rawValue.startsWith('data:') ? rawValue : `data:image/png;base64,${rawValue}`)
  }

  function setMode(nextMode) {
    setModeState(nextMode)

    if (nextMode === 'upload') {
      if (selectedFile) {
        setSelectedFile(selectedFile)
      } else {
        setPreviewUrl('')
      }
      return
    }

    clearObjectUrl()

    const rawValue = base64Input.trim()
    if (!rawValue) {
      setPreviewUrl('')
      return
    }

    setPreviewUrl(rawValue.startsWith('data:') ? rawValue : `data:image/png;base64,${rawValue}`)
  }

  async function submit(event) {
    event.preventDefault()

    if (mode === 'upload' && !selectedFile) {
      setError(defaultErrorMessage)
      setPrediction(null)
      return
    }

    if (mode === 'base64' && !base64Input.trim()) {
      setError('Cole um base64 válido para continuar.')
      setPrediction(null)
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      const data = await predictClimate({
        file: mode === 'upload' ? selectedFile : null,
        imageBase64: mode === 'base64' ? base64Input.trim() : null,
      })
      setPrediction(data)
      if (typeof onSuccess === 'function') {
        onSuccess(data)
      }
    } catch (submissionError) {
      setError(submissionError instanceof Error ? submissionError.message : 'Falha ao enviar a imagem.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function reset() {
    setModeState('upload')
    setSelectedFileState(null)
    setBase64InputState('')
    clearObjectUrl()
    setPreviewUrl('')
    setPrediction(null)
    setError('')
  }

  return {
    mode,
    setMode,
    selectedFile,
    setSelectedFile,
    base64Input,
    setBase64Input,
    previewUrl,
    prediction,
    error,
    isSubmitting,
    submit,
    reset,
  }
}
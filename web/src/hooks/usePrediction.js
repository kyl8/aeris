import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { predictFeatures } from '../lib/api'
import { parseFeatureInput } from '../lib/featureParser'

export function usePrediction(defaultInput = '12, 18, 24') {
  const { t } = useTranslation()
  const [featuresInput, setFeaturesInput] = useState(defaultInput)
  const [prediction, setPrediction] = useState(null)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const parsedFeatures = parseFeatureInput(featuresInput)

  async function submit(event) {
    event.preventDefault()

    if (parsedFeatures.length === 0) {
      setError(t('errors.emptyFeatures'))
      setPrediction(null)
      return
    }

    setIsSubmitting(true)
    setError('')

    try {
      const data = await predictFeatures(parsedFeatures)
      setPrediction(data)
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : t('errors.requestFailed'),
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    featuresInput,
    setFeaturesInput,
    parsedFeatures,
    prediction,
    error,
    isSubmitting,
    submit,
  }
}
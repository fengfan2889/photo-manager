import { useState, useCallback } from 'react'
import { logger } from '../utils/logger'

export interface ErrorState {
  message: string
  detail?: string
}

export function useError() {
  const [error, setError] = useState<ErrorState | null>(null)

  const showError = useCallback((message: string, detail?: string) => {
    logger.error(message, detail ? new Error(detail) : undefined)
    console.error(`[Error] ${message}`, detail || '')
    setError({ message, detail })
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return { error, showError, clearError }
}

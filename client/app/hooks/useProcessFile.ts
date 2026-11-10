"use client"

import { useCallback, useEffect, useState } from "react"
import { Entry } from "../event-logs/columns"

const API_BASE = "http://127.0.0.1:8000"

export type SavedEventLog = {
  id: number
  name: string
  source_filename: string
  imported_at_utc: string
  event_count: number
}

type ImportedEventLog = {
  id: number
}

async function responseError(response: Response): Promise<string> {
  try {
    const body: { detail?: string } = await response.json()
    return body.detail ?? `Request failed with status ${response.status}`
  } catch {
    return `Request failed with status ${response.status}`
  }
}

export const useProcessFile = () => {
  const [eventLogData, setEventLogData] = useState<Entry[]>([])
  const [bpmnXml, setBpmnXml] = useState<string>()
  const [savedEventLogs, setSavedEventLogs] = useState<SavedEventLog[]>([])
  const [error, setError] = useState<string>()
  const [isLoading, setIsLoading] = useState(false)

  const refreshSavedEventLogs = useCallback(async () => {
    const response = await fetch(`${API_BASE}/event-logs`)
    if (!response.ok) throw new Error(await responseError(response))
    setSavedEventLogs(await response.json() as SavedEventLog[])
  }, [])

  useEffect(() => {
    let active = true
    const loadSavedEventLogs = async () => {
      try {
        const response = await fetch(`${API_BASE}/event-logs`)
        if (!response.ok) throw new Error(await responseError(response))
        const logs = await response.json() as SavedEventLog[]
        if (active) setSavedEventLogs(logs)
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load saved event logs")
        }
      }
    }

    void loadSavedEventLogs()
    return () => {
      active = false
    }
  }, [])

  const loadSavedEventLog = useCallback(async (id: number): Promise<boolean> => {
    setIsLoading(true)
    setError(undefined)
    try {
      const [eventsResponse, diagramResponse] = await Promise.all([
        fetch(`${API_BASE}/event-logs/${id}/events`),
        fetch(`${API_BASE}/event-logs/${id}/diagram`),
      ])
      if (!eventsResponse.ok) throw new Error(await responseError(eventsResponse))
      if (!diagramResponse.ok) throw new Error(await responseError(diagramResponse))

      setEventLogData(await eventsResponse.json() as Entry[])
      setBpmnXml(await diagramResponse.text())
      return true
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load saved event log")
      return false
    } finally {
      setIsLoading(false)
    }
  }, [])

  const processFile = useCallback(async (file: File): Promise<boolean> => {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Choose a CSV file.")
      return false
    }

    setIsLoading(true)
    setError(undefined)
    const formData = new FormData()
    formData.append("file", file)
    try {
      const response = await fetch(`${API_BASE}/event-logs`, {
        method: "POST",
        body: formData,
      })
      if (!response.ok) throw new Error(await responseError(response))
      const importedLog = await response.json() as ImportedEventLog
      await refreshSavedEventLogs()

      const [eventsResponse, diagramResponse] = await Promise.all([
        fetch(`${API_BASE}/event-logs/${importedLog.id}/events`),
        fetch(`${API_BASE}/event-logs/${importedLog.id}/diagram`),
      ])
      if (!eventsResponse.ok) throw new Error(await responseError(eventsResponse))
      if (!diagramResponse.ok) throw new Error(await responseError(diagramResponse))
      setEventLogData(await eventsResponse.json() as Entry[])
      setBpmnXml(await diagramResponse.text())
      return true
    } catch (processError) {
      setError(processError instanceof Error ? processError.message : "Unable to import event log")
      return false
    } finally {
      setIsLoading(false)
    }
  }, [refreshSavedEventLogs])

  return {
    eventLogData,
    bpmnXml,
    savedEventLogs,
    error,
    isLoading,
    processFile,
    loadSavedEventLog,
  }
}

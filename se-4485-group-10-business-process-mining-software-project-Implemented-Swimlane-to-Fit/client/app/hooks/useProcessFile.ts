"use client"

import { useState } from "react"
import { Entry } from "../event-logs/columns"

export const useProcessFile = () => {
  const [eventLogData, setEventLogData] = useState<Entry[]>([])
  const [bpmnXml, setBpmnXml] = useState<string>()

  const processFile = async (file: File) => {
    if (!file || file.type != "text/csv") return

    const formData = new FormData()
    formData.append("file", file)

    try {
      const eventLogResponse = await fetch("http://127.0.0.1:8000/event-log", {
        method: "POST",
        body: formData,
      })
      const eventLogJson = await eventLogResponse.json()
      const bpmnDiagramResponse = await fetch("http://127.0.0.1:8000/diagram", {
        method: "POST",
        body: formData,
      })

      const bpmnDiagramXml = await bpmnDiagramResponse.text()

      setEventLogData(eventLogJson)
      setBpmnXml(bpmnDiagramXml)
    } catch (error) {
      console.error(error)
    }
  }

  return {
    eventLogData,
    bpmnXml,
    processFile,
  }
}

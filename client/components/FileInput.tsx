"use client"

import styles from "./FileInput.module.css"
import { useState } from "react"
import { Button } from "./ui/button"
import { Field, FieldDescription } from "./ui/field"
import { Input } from "./ui/input"
import { SavedEventLog } from "@/app/hooks/useProcessFile"

interface FileInputProps {
  onFileSubmit: (file: File) => Promise<boolean>
  onLoadSavedEventLog: (id: number) => Promise<boolean>
  savedEventLogs: SavedEventLog[]
  error?: string
  isLoading: boolean
}

export default function FileInput({
  onFileSubmit,
  onLoadSavedEventLog,
  savedEventLogs,
  error,
  isLoading,
}: FileInputProps) {
  const [file, setFile] = useState<File>()
  const [selectedLogId, setSelectedLogId] = useState("")

  const handleSubmit = async () => {
    if (file) await onFileSubmit(file)
  }

  return (
    <div className="space-y-4">
      <h1 className='text-2xl font-bold'>Upload Event Log</h1>
      <Field className='max-w-sm'>
        <Input
          id='event-log-input'
          type='file'
          accept =".csv"
          className={styles.fileInput}
          onChange={(event) => {
            if (event.target.files && event.target.files.length > 0)
              setFile(event.target.files[0])
          }}
        />
        <FieldDescription>
          Upload a .csv file with your event log.
        </FieldDescription>
      </Field>
      <Button onClick={handleSubmit} disabled={!file || isLoading}>
        {isLoading ? "Saving..." : "Import CSV"}
      </Button>

      <div className="space-y-2 border-t pt-4">
        <h2 className="font-semibold">Saved event logs</h2>
        {savedEventLogs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No saved logs yet.</p>
        ) : (
          <>
            <select
              aria-label="Saved event logs"
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              value={selectedLogId}
              onChange={(event) => setSelectedLogId(event.target.value)}
            >
              <option value="">Select a saved log</option>
              {savedEventLogs.map((log) => (
                <option key={log.id} value={log.id}>
                  {log.name} — {log.event_count} events — {new Date(log.imported_at_utc).toLocaleString()}
                </option>
              ))}
            </select>
            <Button
              variant="outline"
              disabled={!selectedLogId || isLoading}
              onClick={() => void onLoadSavedEventLog(Number(selectedLogId))}
            >
              Load selected log
            </Button>
          </>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

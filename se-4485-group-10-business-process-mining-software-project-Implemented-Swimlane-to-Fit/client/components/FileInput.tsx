"use client"

import styles from "./FileInput.module.css"
import { useContext, useState } from "react"
import { Button } from "./ui/button"
import { Field, FieldDescription, FieldLabel } from "./ui/field"
import { Input } from "./ui/input"

interface FileInputProps {
  onFileSubmit: (file: File) => void
}

export default function FileInput({ onFileSubmit }:FileInputProps) {
  const [file, setFile] = useState<File>()

  const handleSubmit = async () => {
    if (file?.type != "text/csv") return

    onFileSubmit(file)
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
      <Button onClick={handleSubmit}>Submit</Button>
    </div>
  )
}

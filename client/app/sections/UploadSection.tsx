import styles from "./UploadSection.module.css"
import FileInput from "@/components/FileInput"
import { SavedEventLog } from "../hooks/useProcessFile"

interface UploadSectionProps {
  onFileSubmit: (file: File) => Promise<boolean>
  onLoadSavedEventLog: (id: number) => Promise<boolean>
  savedEventLogs: SavedEventLog[]
  error?: string
  isLoading: boolean
  isOpen: boolean
  onClose: () => void
}

export default function UploadSection({
  onFileSubmit,
  onLoadSavedEventLog,
  savedEventLogs,
  error,
  isLoading,
  isOpen,
  onClose,
}: UploadSectionProps) {
  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.wrapper} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onClose}>✕</button>
        <div className={styles.body}>
          <FileInput
            onFileSubmit={onFileSubmit}
            onLoadSavedEventLog={onLoadSavedEventLog}
            savedEventLogs={savedEventLogs}
            error={error}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  )
}
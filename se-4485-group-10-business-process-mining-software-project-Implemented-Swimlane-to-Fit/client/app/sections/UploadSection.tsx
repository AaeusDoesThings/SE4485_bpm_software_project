import styles from "./UploadSection.module.css"
import FileInput from "@/components/FileInput"

interface UploadSectionProps {
  onFileSubmit: (file: File) => void
  isOpen: boolean
  onClose: () => void
}

export default function UploadSection({ onFileSubmit, isOpen, onClose }: UploadSectionProps) {
  if (!isOpen) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.wrapper} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeButton} onClick={onClose}>✕</button>
        <div className={styles.body}>
          <FileInput onFileSubmit={onFileSubmit} />
        </div>
      </div>
    </div>
  )
}
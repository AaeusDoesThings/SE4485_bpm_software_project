import BpmnViewer, { BpmnViewerHandle } from "@/components/BpmnViewer"
import { ColumnDef } from "@tanstack/react-table"
import styles from "./BpmnSection.module.css"
import { RefObject } from "react"

interface BpmnSectionProps<TData, TValue> {
  xml: string
  data: TData[]
  columns: ColumnDef<TData, TValue>[]
  viewerRef: RefObject<BpmnViewerHandle | null>
}

export default function BpmnSection<TData, TValue>({
  xml,
  data,
  columns,
  viewerRef,
}: BpmnSectionProps<TData, TValue>) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.title}>BPMN diagram</h2>
        <p className={styles.subtitle}>
          Generated process model alongside your event log
        </p>
      </div>
      <div className={styles.body}>
        <div className={styles.viewer}>
          <BpmnViewer xml={xml} ref={viewerRef} />
        </div>
      </div>
    </div>
  )
}

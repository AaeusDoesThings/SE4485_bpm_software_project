import { DataTable } from "../event-logs/data-table"
import { ColumnDef } from "@tanstack/react-table"
import styles from "./EventLogSection.module.css"

interface EventLogSectionProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
}

export default function EventLogSection<TData, TValue>({
  columns,
  data,
}: EventLogSectionProps<TData, TValue>) {
  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.title}>Event log</h2>
        <p className={styles.subtitle}>Showing all events from the uploaded file</p>
      </div>
      <div className={styles.body}>
        <div className={styles.tableWrapper}>
          <div className={styles.tableScroll}>
            <DataTable columns={columns} data={data} />
          </div>
        </div>
      </div>
    </div>
  )
}
"use client"

import { useRef, useState, useCallback, useEffect, RefObject } from "react"
import BpmnViewer, { BpmnViewerHandle } from "@/components/BpmnViewer"
import { DataTable } from "../event-logs/data-table"
import { ColumnDef } from "@tanstack/react-table"
import styles from "./OverviewSection.module.css"
import { Entry } from "../event-logs/columns"

interface OverviewSectionProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  xml: string
  onSelectEventLog: () => void
  onSelectBpmn: () => void
  viewerRef: RefObject<BpmnViewerHandle | null>
}

export default function OverviewSection<TData, TValue>({
  columns,
  data,
  xml,
  onSelectEventLog,
  onSelectBpmn,
  viewerRef,
}: OverviewSectionProps<TData, TValue>) {
  const [leftPercent, setLeftPercent] = useState(50)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    dragging.current = true
    document.body.style.cursor = "col-resize"
  }, [])

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const newLeft = ((e.clientX - rect.left) / rect.width) * 100
    setLeftPercent(Math.min(Math.max(newLeft, 20), 80))
  }, [])

  const onPointerUp = useCallback(() => {
    dragging.current = false
    document.body.style.cursor = ""
  }, [])

  const [selectedRow, setSelectedRow] = useState<string | null>(null)

  const handleRowClick = (entry: Entry) => {
    const newActivity = selectedRow === entry.Activity ? null : entry.Activity

    console.log(newActivity)

    setSelectedRow(newActivity)
    viewerRef.current?.highlightActivity(newActivity)
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <h2 className={styles.title}>Overview</h2>
        <p className={styles.subtitle}>Drag the divider to resize panels</p>
      </div>

      <div ref={containerRef} className={styles.panelGroup}>
        {/* Event log panel */}
        <div
          className={styles.panel}
          style={{ width: `${leftPercent}%`, flexShrink: 0 }}
        >
          <div
            className={styles.panelHeader}
            onClick={onSelectEventLog}
            style={{ cursor: "pointer" }}
          >
            <span className={styles.panelTitle}>Event log</span>
            <span className={styles.panelNav}>Expand ⌞ ⌝</span>
          </div>
          <div className={styles.panelBody}>
            <DataTable
              columns={columns}
              data={data}
              handleRowClick={handleRowClick}
            />
          </div>
        </div>

        {/* Drag handle */}

        <div
          className={styles.resizeHandle}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
        />

        {/* BPMN panel */}
        <div className={styles.panel} style={{ flex: 1, minWidth: 0 }}>
          <div
            className={styles.panelHeader}
            onClick={onSelectBpmn}
            style={{ cursor: "pointer" }}
          >
            <span className={styles.panelTitle}>BPMN diagram</span>
            <span className={styles.panelNav}>Expand ⌞ ⌝</span>
          </div>
          <div className={styles.panelBody}>
            <BpmnViewer xml={xml} ref={viewerRef} />
          </div>
        </div>
      </div>
    </div>
  )
}

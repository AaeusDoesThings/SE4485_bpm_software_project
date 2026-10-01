"use client"

import { ColumnDef } from "@tanstack/react-table"

export type Entry = {
  Case_ID: string
  Activity: string
  Timestamp: Date
}

export const columns: ColumnDef<Entry>[] = [
  {
    accessorKey: "Case_ID",
    header: "Case ID",
  },
  {
    accessorKey: "Activity",
    header: "Activity",
  },
  {
    accessorKey: "Timestamp",
    header: "Timestamp",
  },
  {
    accessorKey: "Role",
    header: "Role",
  },
]

"use client"

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react"
import Modeler from "bpmn-js/lib/Modeler"
import "bpmn-js/dist/assets/diagram-js.css"
import "bpmn-font/dist/css/bpmn-embedded.css"
import "bpmn-js/dist/assets/bpmn-js.css"
import { Button } from "./ui/button"

import dagre from "dagre"

interface BpmnViewerProps {
  xml?: string
}

export interface BpmnViewerHandle {
  highlightActivity: (activityName: string | null) => void
}

function injectLanes(
  xml: string,
  roleToActivities: Record<string, string[]>,
): string {
  const parser = new DOMParser()
  const doc = parser.parseFromString(xml, "application/xml")

  const BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
  const BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
  const DC = "http://www.omg.org/spec/DD/20100524/DC"

  const process = doc.getElementsByTagNameNS(BPMN, "process")[0]
  const plane = doc.getElementsByTagNameNS(BPMNDI, "BPMNPlane")[0]

  if (!process || !plane) return xml // nothing to do

  // Build activityName -> elementId from existing process children
  const nameToId: Record<string, string> = {}
  const idToElement: Record<string, Element> = {}
  Array.from(process.children).forEach((el) => {
    const name = el.getAttribute("name")
    const id = el.getAttribute("id")
    if (name && id) {
      nameToId[name] = id
      idToElement[id] = el
    }
  })

  // Remove any stale laneSets
  Array.from(process.getElementsByTagNameNS(BPMN, "laneSet")).forEach((ls) =>
    ls.parentNode?.removeChild(ls),
  )

  // Build <laneSet>
  const laneSet = doc.createElementNS(BPMN, "laneSet")
  laneSet.setAttribute("id", "laneSet_1")

  Object.entries(roleToActivities).forEach(([role, activities], idx) => {
    const laneId = `lane_${role.replace(/\s+/g, "_")}`

    const lane = doc.createElementNS(BPMN, "lane")
    lane.setAttribute("id", laneId)
    lane.setAttribute("name", role)

    activities.forEach((actName) => {
      const nodeId = nameToId[actName]
      if (!nodeId) return
      const ref = doc.createElementNS(BPMN, "flowNodeRef")
      ref.textContent = nodeId
      lane.appendChild(ref)
    })
    // Assign control nodes (start/end/gateway) that point to this lane's activities
    const assignedIds = new Set(
      activities.map((a) => nameToId[a]).filter(Boolean),
    )

    Array.from(process.children).forEach((el) => {
      const id = el.getAttribute("id")
      if (!id || assignedIds.has(id)) return

      const localName = el.localName.toLowerCase()
      const isControlNode =
        localName.includes("startevent") ||
        localName.includes("endevent") ||
        localName.includes("gateway") ||
        localName.includes("intermediatecatch") ||
        localName.includes("intermediatethrow")

      if (!isControlNode) return

      // Check if this control node points to any activity in this lane
      const outgoing = Array.from(process.children).filter(
        (sf) =>
          sf.localName.toLowerCase().includes("sequenceflow") &&
          sf.getAttribute("sourceRef") === id,
      )

      for (const sf of outgoing) {
        const targetId = sf.getAttribute("targetRef")
        if (targetId && assignedIds.has(targetId)) {
          const ref = doc.createElementNS(BPMN, "flowNodeRef")
          ref.textContent = id
          lane.appendChild(ref)
          assignedIds.add(id)
          break
        }
      }

      // Fallback: check incoming (for end events)
      if (!assignedIds.has(id)) {
        const incoming = Array.from(process.children).filter(
          (sf) =>
            sf.localName === "sequenceFlow" &&
            sf.getAttribute("targetRef") === id,
        )
        for (const sf of incoming) {
          const sourceId = sf.getAttribute("sourceRef")
          if (sourceId && assignedIds.has(sourceId)) {
            const ref = doc.createElementNS(BPMN, "flowNodeRef")
            ref.textContent = id
            lane.appendChild(ref)
            assignedIds.add(id)
            break
          }
        }
      }
    })
    laneSet.appendChild(lane)

    // Placeholder BPMNShape for the lane (dagre will overwrite bounds)
    const shape = doc.createElementNS(BPMNDI, "BPMNShape")
    shape.setAttribute("id", `${laneId}_di`)
    shape.setAttribute("bpmnElement", laneId)
    shape.setAttribute("isHorizontal", "true")

    const bounds = doc.createElementNS(DC, "Bounds")
    bounds.setAttribute("x", "0")
    bounds.setAttribute("y", "0")
    bounds.setAttribute("width", "800")
    bounds.setAttribute("height", "150")
    shape.appendChild(bounds)
    plane.insertBefore(shape, plane.firstChild)
  })

  // Insert laneSet as first child of process
  process.insertBefore(laneSet, process.firstChild)

  return new XMLSerializer().serializeToString(doc)
}

/**
 * Runs a dagre compound layout over the live bpmn-js element registry and
 * writes positions back via the modeling API.
 *
 * Lanes become compound parent nodes; tasks/events/gateways are children.
 * Sequence flows become edges.
 */
async function applyDagreLayout(modeler: Modeler): Promise<void> {
  const NODESEP = 30
  const EDGESEP = 30
  const RANKSEP = 85

  // ── 1. Get raw moddle definitions (same as pm4py's approach) ──────────────
  const definitions = (modeler as any)._definitions
  const rootProcess = definitions.rootElements.find(
    (el: any) => el.$type === "bpmn:Process",
  )
  if (!rootProcess) return

  const flowElements: any[] = rootProcess.flowElements ?? []
  const planeElements: any[] = definitions.diagrams[0].plane.planeElement ?? []

  // Build index: bpmnElement.id -> index in planeElements
  const graphicalDict: Record<string, number> = {}
  const edgesDict: Record<string, string> = {} // "srcId@tgtId" -> sequenceFlow id

  planeElements.forEach((pe: any, i: number) => {
    const id = pe.bpmnElement?.id
    if (id) graphicalDict[id] = i
  })

  // ── 2. DFS from start event (same traversal as pm4py) ────────────────────
  const startEvent = flowElements.find((n: any) =>
    n.$type?.toLowerCase().endsWith("startevent"),
  )
  if (!startEvent) return

  const visited: any[] = []
  const toVisit: any[] = [startEvent]

  while (toVisit.length > 0) {
    const el = toVisit.pop()
    if (!visited.includes(el)) visited.push(el)
    if (el.outgoing) {
      for (const out of el.outgoing) {
        // Record edge: "sourceId@targetId" -> flowId
        edgesDict[`${el.id}@${out.targetRef.id}`] = out.id
        if (!visited.includes(out.targetRef)) {
          toVisit.push(out.targetRef)
        }
      }
    }
  }

  // ── 3. Build lane membership map: nodeId -> laneId ───────────────────────
  const nodeToLane: Record<string, string> = {}
  const laneSets: any[] = rootProcess.laneSets ?? []
  laneSets.forEach((ls: any) => {
    ;(ls.lanes ?? []).forEach((lane: any) => {
      ;(lane.flowNodeRef ?? []).forEach((ref: any) => {
        nodeToLane[ref.id] = lane.id
      })
    })
  })

  const lanes: any[] = laneSets.flatMap((ls: any) => ls.lanes ?? [])

  // ── Helper: run one dagre pass and return the graph ───────────────────────
  const runDagre = (
    forcedLaneWidth?: number,
    forcedLaneHeight?: number,
  ): dagre.graphlib.Graph => {
    const g = new dagre.graphlib.Graph({ compound: true, multigraph: false })
    g.setGraph({
      rankdir: "LR",
      nodesep: NODESEP,
      edgesep: EDGESEP,
      ranksep: RANKSEP,
    })
    g.setDefaultEdgeLabel(() => ({}))

    // Add lane compound nodes — these get the forced dimensions on 2nd pass
    lanes.forEach((lane: any) => {
      const pe = planeElements[graphicalDict[lane.id]]
      const w = forcedLaneWidth ?? pe?.bounds?.width ?? 800
      const h = forcedLaneHeight ?? pe?.bounds?.height ?? 150

      console.log(w)
      g.setNode(lane.id, { label: lane.name ?? lane.id, width: w, height: h })
    })

    // Add flow nodes — always use their ORIGINAL bounds, never scale them
    visited.forEach((el: any) => {
      const pe = planeElements[graphicalDict[el.id]]
      if (!pe?.bounds) return
      g.setNode(el.id, {
        label: el.name ?? el.id,
        width: pe.bounds.width, // always original, no forced scaling
        height: pe.bounds.height,
      })

      const laneId = nodeToLane[el.id]
      if (laneId) g.setParent(el.id, laneId)
    })

    // Add edges
    flowElements
      .filter((el: any) => el.$type === "bpmn:SequenceFlow")
      .forEach((flow: any) => {
        const src = flow.sourceRef?.id
        const tgt = flow.targetRef?.id
        if (src && tgt && g.hasNode(src) && g.hasNode(tgt)) {
          g.setEdge(src, tgt, { id: flow.id })
        }
      })

    dagre.layout(g)
    return g
  }

  // ── 4. First pass: measure how large dagre makes the lane containers ───────
  const g1 = runDagre()

  let maxLaneWidth = 0
  let maxLaneHeight = 0

  // Only measure lane nodes, not flow nodes
  lanes.forEach((lane: any) => {
    const n = g1.node(lane.id)
    if (!n) return
    maxLaneWidth = Math.max(maxLaneWidth, n.width)
    maxLaneHeight = Math.max(maxLaneHeight, n.height)
  })

  console.log(maxLaneWidth, maxLaneHeight)

  // ── 5. Second pass: expand lanes with pm4py's multipliers ─────────────────
  const g2 = runDagre(maxLaneWidth * 1.7, maxLaneHeight * 0.87)

  const targetWidth = maxLaneWidth * 1.2

  lanes.forEach((lane: any) => {
    const n = g2.node(lane.id)
    if (n) {
      const oldWidth = n.width
      n.width = targetWidth
      // Adjust x position to maintain centering
      n.x = n.x - (oldWidth - targetWidth) / 2
    }
  })

  const minLeftEdge = Math.min(
    ...lanes.map((lane) => {
      const n = g2.node(lane.id)
      return n.x - n.width / 2
    }),
  )

  lanes.forEach((lane) => {
    const n = g2.node(lane.id)
    const oldWidth = n.width
    const currentLeftEdge = n.x - oldWidth / 2
    const shift = minLeftEdge - currentLeftEdge
    n.x = n.x + shift
  })

  // ── 6. Write node positions back to moddle bounds ─────────────────────────
  g2.nodes().forEach((nodeId) => {
    const n = g2.node(nodeId)
    const idx = graphicalDict[nodeId]
    if (!n || idx === undefined) return

    const pe = planeElements[idx]
    if (!pe?.bounds) return

    console.log(n)

    pe.bounds.x = n.x - n.width / 2
    pe.bounds.y = n.y - n.height / 2
    pe.bounds.width = n.width
    pe.bounds.height = n.height
  })

  // ── 7. Write edge waypoints, cloning metadata from existing waypoints ──────
  // (same pattern as pm4py's CustomWaypoint clone)
  g2.edges().forEach((edgeObj) => {
    const key = `${edgeObj.v}@${edgeObj.w}`
    const flowId = edgesDict[key]
    const idx = graphicalDict[flowId]
    if (flowId === undefined || idx === undefined) return

    const pe = planeElements[idx]
    const edgeData = g2.edge(edgeObj)
    const referenceWp = pe?.waypoint?.[0]
    if (!pe || !edgeData?.points || !referenceWp) return

    pe.waypoint = edgeData.points.map((p: { x: number; y: number }) => {
      // Clone all moddle metadata from the reference waypoint
      // so the serializer doesn't reject the new points
      const wp: any = Object.create(Object.getPrototypeOf(referenceWp))
      Object.assign(wp, referenceWp)
      wp.x = p.x
      wp.y = p.y
      return wp
    })
  })

  // ── 8. Re-import the mutated XML to force bpmn-js to re-render ────────────
  const { xml: updatedXml } = await (modeler as any).saveXML({ format: false })
  await modeler.importXML(updatedXml)
}

const BpmnViewer = forwardRef(({ xml }: BpmnViewerProps, ref) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const [bpmnModeler, setBpmnModeler] = useState<Modeler | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize bpmn-js Modeler
  useEffect(() => {
    if (!containerRef.current) return

    // Create Modeler instance
    const modeler = new Modeler({
      container: containerRef.current,
    })

    setBpmnModeler(modeler)

    // Cleanup function
    return () => {
      modeler.destroy()
    }
  }, [])

  // Fetch BPMN from API and render
  const loadBpmnDiagram = async () => {
    if (!bpmnModeler) return

    setLoading(true)
    setError(null)

    try {
      if (!xml) return

      const parser = new DOMParser()
      const doc = parser.parseFromString(xml, "application/xml")
      const BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
      const processEl = doc.getElementsByTagNameNS(BPMN, "process")[0]
      const roleMapRaw = processEl?.getAttribute("data-role-map")
      const roleToActivities: Record<string, string[]> = roleMapRaw
        ? JSON.parse(roleMapRaw)
        : {}

      // 2. Inject lanes into the XML before importing
      const enrichedXml =
        Object.keys(roleToActivities).length > 0
          ? injectLanes(xml, roleToActivities)
          : xml

      const bpmnXML = enrichedXml

      // Import XML into bpmn-js
      await bpmnModeler.importXML(bpmnXML)
      await applyDagreLayout(bpmnModeler)

      // Optional: Fit diagram to view
      const canvas = bpmnModeler.get("canvas") as {
        zoom: (fit: "fit-viewport", padding: number | "auto") => void
      }
      canvas.zoom("fit-viewport", "auto")
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load BPMN diagram",
      )
      console.error("Error loading BPMN:", err)
    } finally {
      setLoading(false)
    }
  }

  // Load diagram when modeler is ready
  useEffect(() => {
    if (bpmnModeler) {
      loadBpmnDiagram()
    }
  }, [bpmnModeler, xml])

  useImperativeHandle(ref, () => ({
    highlightActivity: (activityName: string | null) => {
      if (!bpmnModeler) return

      console.log("attempting to highlight: ", activityName)

      const elementRegistry = bpmnModeler.get<any>("elementRegistry")
      const canvas = bpmnModeler.get<any>("canvas")

      // Clear all previous highlights
      elementRegistry.getAll().forEach((el: any) => {
        if (el.type !== "bpmn:SequenceFlow") {
          canvas.removeMarker(el.id, "highlighted-node")
        }
      })

      if (!activityName) return

      // Find element(s) whose name matches the activity
      const matches = elementRegistry
        .getAll()
        .filter(
          (el: any) =>
            el.businessObject?.name === activityName &&
            el.type !== "bpmn:SequenceFlow",
        )

      matches.forEach((el: any) => {
        console.log(el)
        canvas.addMarker(el.id, "highlighted-node")
        // Scroll the element into view
        canvas.scrollToElement(el)
      })
    },
  }))

  return (
    <div className='w-full h-full flex flex-col'>
      {/* Controls */}
      <div className='bg-white border-b p-4 flex gap-2'>
        <Button
          onClick={loadBpmnDiagram}
          disabled={loading}
          className='px-4 py-2 bg-blue-500 text-white hover:bg-blue-600 disabled:bg-gray-400'
        >
          {loading ? "Loading..." : "Refresh Diagram"}
        </Button>

        {/* Optional: Download button */}
        <Button
          onClick={async () => {
            try {
              const { svg } = await bpmnModeler!.saveSVG()
              const blob = new Blob([svg], { type: "image/svg+xml" })
              const url = URL.createObjectURL(blob)
              const a = document.createElement("a")
              a.href = url
              a.download = "diagram.svg"
              a.click()
              URL.revokeObjectURL(url)
            } catch (err) {
              console.error("Failed to save diagram:", err)
            }
          }}
          className='px-4 py-2 bg-green-500 text-white hover:bg-green-600'
        >
          Download Diagram
        </Button>
        <Button
          onClick={async () => {
            try {
              const { svg } = await bpmnModeler!.saveSVG()
              const blob = new Blob([svg], { type: "image/svg+xml" })

              const clipboardItem = new ClipboardItem({
                [blob.type]: blob,
              })

              await navigator.clipboard.write([clipboardItem])
            } catch (err) {
              console.error("Failed to save diagram:", err)
            }
          }}
          className='px-4 py-2 bg-green-500 text-white hover:bg-green-600'
        >
          Copy Diagram
        </Button>

        <Button
          onClick={() => (bpmnModeler?.get("zoomScroll") as any)?.stepZoom(1)}
          disabled={!bpmnModeler}
          className='px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200'
        >
          +
        </Button>

        <Button
          onClick={() => (bpmnModeler?.get("zoomScroll") as any)?.stepZoom(-1)}
          disabled={!bpmnModeler}
          className='px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200'
        >
          -
        </Button>

        <Button
          onClick={() => (bpmnModeler?.get("canvas") as any)?.zoom("fit-viewport", "auto")}
          disabled={!bpmnModeler}
          className='px-4 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200'
        >
          Fit
        </Button>
      </div>

      {/* Error display */}
      {error && (
        <div className='bg-red-100 border border-red-400 text-red-700 px-4 py-3 m-4 rounded'>
          {error}
        </div>
      )}

      {/* BPMN container */}
      <div
        ref={containerRef}
        className='flex-1 min-h-0 w-full bg-gray-50'
      />
    </div>
  )
})

BpmnViewer.displayName = "BpmnViewer"
export default BpmnViewer

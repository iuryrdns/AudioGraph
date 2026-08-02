"use client"

import type React from "react"
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react"
import { Maximize2, Target, Eye, EyeOff, Play, Info } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"

type Pos = { x: number; y: number; vx: number; vy: number }

type Props = {
  nodes: GraphNode[]
  selectedId: string | null
  playingId: string | null
  onSelect: (id: string) => void
  onExpand: (id: string) => void
  onOpenDetails?: (node: GraphNode) => void
}

const RADIUS = (depth: number) => (depth === 0 ? 36 : depth === 1 ? 28 : 23)
const LINK_LENGTH = (depth: number) => (depth === 1 ? 175 : 140)

export function RecommendationGraph({
  nodes,
  selectedId,
  playingId,
  onSelect,
  onExpand,
  onOpenDetails,
}: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null)
  const posRef = useRef<Map<string, Pos>>(new Map())
  const alphaRef = useRef(1)
  const frameRef = useRef<number | null>(null)
  const dragRef = useRef<{ id: string; moved: boolean } | null>(null)
  const panRef = useRef<{ x: number; y: number } | null>(null)

  const [size, setSize] = useState({ width: 800, height: 600 })
  const [, setTick] = useState(0)
  const [view, setView] = useState({ x: 0, y: 0, k: 1 })
  const [hideDisliked, setHideDisliked] = useState(false)
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null)

  const visibleNodes = hideDisliked
    ? nodes.filter((n) => n.feedback !== "dislike")
    : nodes

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // garante posição inicial para novos nós (nascem perto do pai)
  useEffect(() => {
    const cx = size.width / 2
    const cy = size.height / 2
    let added = false
    nodes.forEach((node, index) => {
      if (posRef.current.has(node.id)) return
      added = true
      const parent = node.parentId ? posRef.current.get(node.parentId) : undefined
      const angle = (index * 2.399) % (Math.PI * 2)
      const spread = parent ? 70 : 10
      posRef.current.set(node.id, {
        x: (parent?.x ?? cx) + Math.cos(angle) * spread,
        y: (parent?.y ?? cy) + Math.sin(angle) * spread,
        vx: 0,
        vy: 0,
      })
    })
    const ids = new Set(nodes.map((n) => n.id))
    for (const id of Array.from(posRef.current.keys())) {
      if (!ids.has(id)) posRef.current.delete(id)
    }
    if (added) alphaRef.current = 1
  }, [nodes, size.width, size.height])

  // simulação de forças
  useEffect(() => {
    const step = () => {
      const positions = posRef.current
      const alpha = alphaRef.current
      const cx = size.width / 2
      const cy = size.height / 2

      if (alpha > 0.005) {
        // repulsão
        for (let i = 0; i < visibleNodes.length; i++) {
          const a = positions.get(visibleNodes[i].id)
          if (!a) continue
          for (let j = i + 1; j < visibleNodes.length; j++) {
            const b = positions.get(visibleNodes[j].id)
            if (!b) continue
            let dx = b.x - a.x
            let dy = b.y - a.y
            let dist = Math.hypot(dx, dy)
            if (dist < 0.01) {
              dx = Math.random() - 0.5
              dy = Math.random() - 0.5
              dist = 1
            }
            const minDist = RADIUS(visibleNodes[i].depth) + RADIUS(visibleNodes[j].depth) + 62
            const force = (3400 / (dist * dist) + (dist < minDist ? (minDist - dist) * 0.55 : 0)) * alpha
            const fx = (dx / dist) * force
            const fy = (dy / dist) * force
            a.vx -= fx
            a.vy -= fy
            b.vx += fx
            b.vy += fy
          }
        }

        // molas nas arestas + gravidade ao centro
        for (const node of visibleNodes) {
          const p = positions.get(node.id)
          if (!p) continue
          if (node.parentId) {
            const parent = positions.get(node.parentId)
            if (parent) {
              const dx = p.x - parent.x
              const dy = p.y - parent.y
              const dist = Math.hypot(dx, dy) || 1
              const target = LINK_LENGTH(node.depth)
              const force = (dist - target) * 0.045 * alpha
              const fx = (dx / dist) * force
              const fy = (dy / dist) * force
              p.vx -= fx
              p.vy -= fy
              parent.vx += fx * 0.6
              parent.vy += fy * 0.6
            }
          }
          const gravity = node.depth === 0 ? 0.05 : 0.006
          p.vx += (cx - p.x) * gravity * alpha
          p.vy += (cy - p.y) * gravity * alpha
        }

        // integração
        for (const node of visibleNodes) {
          const p = positions.get(node.id)
          if (!p) continue
          if (dragRef.current?.id === node.id) {
            p.vx = 0
            p.vy = 0
            continue
          }
          p.vx *= 0.82
          p.vy *= 0.82
          p.x += Math.max(-24, Math.min(24, p.vx))
          p.y += Math.max(-24, Math.min(24, p.vy))
        }

        alphaRef.current = alpha * 0.99
        setTick((t) => t + 1)
      }

      frameRef.current = requestAnimationFrame(step)
    }

    frameRef.current = requestAnimationFrame(step)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
  }, [visibleNodes, size.width, size.height])

  const zoomToFit = useCallback(() => {
    if (visibleNodes.length === 0) return
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    for (const node of visibleNodes) {
      const p = posRef.current.get(node.id)
      if (!p) continue
      minX = Math.min(minX, p.x)
      maxX = Math.max(maxX, p.x)
      minY = Math.min(minY, p.y)
      maxY = Math.max(maxY, p.y)
    }
    if (minX === Infinity) return
    const graphWidth = Math.max(maxX - minX, 100)
    const graphHeight = Math.max(maxY - minY, 100)
    const padding = 120
    const scaleX = (size.width - padding) / graphWidth
    const scaleY = (size.height - padding) / graphHeight
    const k = Math.min(Math.max(Math.min(scaleX, scaleY), 0.4), 1.5)
    const centerX = (minX + maxX) / 2
    const centerY = (minY + maxY) / 2
    setView({
      k,
      x: size.width / 2 - centerX * k,
      y: size.height / 2 - centerY * k,
    })
  }, [visibleNodes, size.width, size.height])

  const centerSeed = useCallback(() => {
    const root = visibleNodes.find((n) => n.depth === 0)
    if (!root) return
    const p = posRef.current.get(root.id)
    if (!p) return
    setView({
      k: 1,
      x: size.width / 2 - p.x,
      y: size.height / 2 - p.y,
    })
  }, [visibleNodes, size.width, size.height])

  const toGraphCoords = useCallback(
    (clientX: number, clientY: number) => {
      const rect = wrapperRef.current?.getBoundingClientRect()
      if (!rect) return { x: 0, y: 0 }
      return {
        x: (clientX - rect.left - view.x) / view.k,
        y: (clientY - rect.top - view.y) / view.k,
      }
    },
    [view],
  )

  const handleNodePointerDown = (event: React.PointerEvent, id: string) => {
    event.stopPropagation()
    ;(event.target as Element).setPointerCapture?.(event.pointerId)
    dragRef.current = { id, moved: false }
  }

  const handlePointerMove = (event: React.PointerEvent) => {
    if (dragRef.current) {
      const p = posRef.current.get(dragRef.current.id)
      if (!p) return
      const { x, y } = toGraphCoords(event.clientX, event.clientY)
      if (Math.hypot(x - p.x, y - p.y) > 4) dragRef.current.moved = true
      p.x = x
      p.y = y
      p.vx = 0
      p.vy = 0
      alphaRef.current = Math.max(alphaRef.current, 0.35)
      setTick((t) => t + 1)
      return
    }
    if (panRef.current) {
      setView((v) => ({
        ...v,
        x: v.x + event.clientX - panRef.current!.x,
        y: v.y + event.clientY - panRef.current!.y,
      }))
      panRef.current = { x: event.clientX, y: event.clientY }
    }
  }

  const handlePointerUp = () => {
    dragRef.current = null
    panRef.current = null
  }

  const handleWheel = (event: React.WheelEvent) => {
    event.preventDefault()
    const rect = wrapperRef.current?.getBoundingClientRect()
    if (!rect) return
    const mx = event.clientX - rect.left
    const my = event.clientY - rect.top
    setView((v) => {
      const k = Math.min(2.2, Math.max(0.4, v.k * (event.deltaY < 0 ? 1.08 : 0.93)))
      return {
        k,
        x: mx - ((mx - v.x) / v.k) * k,
        y: my - ((my - v.y) / v.k) * k,
      }
    })
  }

  const positions = posRef.current

  return (
    <div
      ref={wrapperRef}
      className="relative h-full w-full touch-none overflow-hidden select-none"
      onPointerDown={(event) => {
        panRef.current = { x: event.clientX, y: event.clientY }
      }}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerUp}
      onWheel={handleWheel}
    >
      <svg
        width={size.width}
        height={size.height}
        role="img"
        aria-label="Grafo de recomendações musicais"
        className="block"
      >
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M32 0H0v32" fill="none" stroke="var(--border)" strokeWidth="1" />
          </pattern>
          {visibleNodes.map((node) => (
            <pattern key={node.id} id={`art-${node.id}`} width="1" height="1" patternContentUnits="objectBoundingBox">
              <image
                href={node.track.artwork}
                width="1"
                height="1"
                preserveAspectRatio="xMidYMid slice"
                crossOrigin="anonymous"
              />
            </pattern>
          ))}
        </defs>

        <rect width={size.width} height={size.height} fill="url(#grid)" opacity="0.35" />

        <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          {visibleNodes.map((node) => {
            if (!node.parentId) return null
            const p = positions.get(node.id)
            const parent = positions.get(node.parentId)
            if (!p || !parent) return null
            const isPlayingEdge = node.id === playingId || node.id === selectedId
            const stroke =
              node.feedback === "like"
                ? "var(--color-primary)"
                : node.feedback === "dislike"
                  ? "var(--color-destructive)"
                  : isPlayingEdge
                    ? "var(--color-primary)"
                    : "var(--color-chart-4)"
            const mx = (p.x + parent.x) / 2
            const my = (p.y + parent.y) / 2 - 18
            return (
              <path
                key={`link-${node.id}`}
                d={`M ${parent.x} ${parent.y} Q ${mx} ${my} ${p.x} ${p.y}`}
                fill="none"
                stroke={stroke}
                strokeWidth={isPlayingEdge ? 2.5 : node.feedback ? 2 : 1.25}
                strokeOpacity={node.feedback === "dislike" ? 0.45 : node.feedback === "like" || isPlayingEdge ? 0.9 : 0.4}
                strokeDasharray={node.feedback === "dislike" ? "4 4" : isPlayingEdge ? "6 4" : undefined}
              />
            )
          })}

          {visibleNodes.map((node) => {
            const p = positions.get(node.id)
            if (!p) return null
            const r = RADIUS(node.depth)
            const isSelected = node.id === selectedId
            const isPlaying = node.id === playingId
            const ring =
              node.feedback === "like"
                ? "var(--color-primary)"
                : node.feedback === "dislike"
                  ? "var(--color-destructive)"
                  : isSelected
                    ? "var(--color-foreground)"
                    : "var(--color-border)"
            return (
              <g
                key={node.id}
                transform={`translate(${p.x},${p.y})`}
                className="cursor-pointer"
                onPointerDown={(event) => handleNodePointerDown(event, node.id)}
                onPointerUp={(event) => {
                  event.stopPropagation()
                  if (!dragRef.current?.moved) onSelect(node.id)
                  dragRef.current = null
                }}
                onPointerEnter={() => setHoveredNode(node)}
                onPointerLeave={() => setHoveredNode(null)}
                onDoubleClick={() => onExpand(node.id)}
                opacity={node.feedback === "dislike" ? 0.55 : 1}
              >
                {isPlaying && (
                  <circle r={r + 10} fill="none" stroke="var(--color-primary)" strokeWidth="1.5" opacity="0.5">
                    <animate attributeName="r" values={`${r + 6};${r + 16};${r + 6}`} dur="1.8s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.6;0;0.6" dur="1.8s" repeatCount="indefinite" />
                  </circle>
                )}
                <circle r={r} fill={`url(#art-${node.id})`} />
                <circle r={r} fill="none" stroke={ring} strokeWidth={isSelected || node.feedback ? 3 : 1.5} />

                {node.loading && (
                  <circle r={r + 6} fill="none" stroke="var(--color-primary)" strokeWidth="2" strokeDasharray="6 10">
                    <animateTransform
                      attributeName="transform"
                      type="rotate"
                      from="0"
                      to="360"
                      dur="1.2s"
                      repeatCount="indefinite"
                    />
                  </circle>
                )}

                {node.feedback && (
                  <g transform={`translate(${r * 0.72},${-r * 0.72})`}>
                    <circle
                      r="10"
                      fill={node.feedback === "like" ? "var(--color-primary)" : "var(--color-destructive)"}
                      stroke="var(--color-background)"
                      strokeWidth="2"
                    />
                    <path
                      d={node.feedback === "like" ? "M -4 0 L -1 3 L 4.5 -3" : "M -3.5 -3.5 L 3.5 3.5 M 3.5 -3.5 L -3.5 3.5"}
                      fill="none"
                      stroke={node.feedback === "like" ? "var(--color-primary-foreground)" : "var(--color-background)"}
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </g>
                )}

                <text
                  y={r + 16}
                  textAnchor="middle"
                  className="fill-foreground text-[11px] font-medium"
                  style={{ paintOrder: "stroke", stroke: "var(--color-background)", strokeWidth: 4 }}
                >
                  {truncate(node.track.name, 22)}
                </text>
                <text
                  y={r + 29}
                  textAnchor="middle"
                  className="fill-muted-foreground font-mono text-[9px] uppercase"
                  style={{ paintOrder: "stroke", stroke: "var(--color-background)", strokeWidth: 4 }}
                >
                  {truncate(node.track.artist, 20)}
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Hover Tooltip Floating Card */}
      {hoveredNode && (
        <div className="absolute top-4 left-4 z-20 flex items-center gap-3 rounded-xl border border-border bg-card/90 p-3 shadow-xl backdrop-blur animate-in fade-in duration-150">
          <img
            src={hoveredNode.track.artwork}
            alt=""
            className="size-12 rounded-lg object-cover"
          />
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-foreground">{hoveredNode.track.name}</span>
            <span className="text-[11px] text-muted-foreground">{hoveredNode.track.artist}</span>
            <span className="font-mono text-[10px] text-primary">{hoveredNode.track.genre}</span>
          </div>
          <div className="flex items-center gap-1 ml-2">
            <Button
              size="icon"
              variant="ghost"
              className="size-8 rounded-full"
              title="Tocar nó"
              onClick={() => onSelect(hoveredNode.id)}
            >
              <Play className="size-4 fill-foreground" />
            </Button>
            {onOpenDetails && (
              <Button
                size="icon"
                variant="ghost"
                className="size-8 rounded-full"
                title="Ver detalhes"
                onClick={() => onOpenDetails(hoveredNode)}
              >
                <Info className="size-4" />
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Floating Toolbar Controls */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 rounded-xl border border-border bg-card/80 p-1.5 shadow-lg backdrop-blur">
        <Button
          variant="ghost"
          size="icon"
          className="size-8 rounded-lg"
          title="Ajustar Zoom"
          onClick={zoomToFit}
        >
          <Maximize2 className="size-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="size-8 rounded-lg"
          title="Centralizar Semente"
          onClick={centerSeed}
        >
          <Target className="size-4" />
        </Button>
        <Button
          variant={hideDisliked ? "secondary" : "ghost"}
          size="icon"
          className="size-8 rounded-lg"
          title={hideDisliked ? "Mostrar Rejeitadas" : "Ocultar Rejeitadas"}
          onClick={() => setHideDisliked((prev) => !prev)}
        >
          {hideDisliked ? <EyeOff className="size-4 text-destructive" /> : <Eye className="size-4" />}
        </Button>
      </div>

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-md border border-border bg-card/80 px-2 py-1 font-mono text-[10px] uppercase tracking-wider text-muted-foreground backdrop-blur">
        clique: selecionar · duplo clique: expandir · arraste: mover · scroll: zoom
      </div>
    </div>
  )
}

function truncate(value: string, max: number) {
  const clean = value.replace(/\s*\(feat\..*?\)/i, "")
  return clean.length > max ? `${clean.slice(0, max - 1)}…` : clean
}

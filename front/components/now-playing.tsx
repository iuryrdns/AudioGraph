"use client"

import { AudioLines, Info, Loader2, Network } from "lucide-react"
import { AudioVisualizer } from "@/components/audio-visualizer"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"

type Props = {
  node: GraphNode
  path: GraphNode[]
  isPlaying: boolean
  childrenCount: number
  onExpand: () => void
  onOpenDetails?: () => void
}

export function NowPlaying({ node, path, isPlaying, childrenCount, onExpand, onOpenDetails }: Props) {
  return (
    <div className="relative flex h-full flex-col items-center justify-center gap-6 overflow-y-auto px-6 py-8">
      <div className="relative">
        <img
          src={node.track.artwork || "/placeholder.svg"}
          alt={`Capa de ${node.track.album || node.track.name}`}
          className="size-56 rounded-2xl border border-border object-cover shadow-2xl sm:size-72"
        />
        {isPlaying && (
          <span className="absolute -bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-primary shadow-lg">
            <AudioLines className="size-3 animate-pulse" aria-hidden="true" />
            tocando
          </span>
        )}
      </div>

      <AudioVisualizer isPlaying={isPlaying} barCount={20} className="h-8" />

      <div className="flex max-w-md flex-col items-center gap-1.5 text-center">
        <p className="font-mono text-[10px] uppercase tracking-widest text-primary">
          {node.depth === 0 ? "Sua semente" : `Recomendação · nível ${node.depth}`}
        </p>
        <h2 className="text-2xl font-semibold leading-tight text-foreground text-balance sm:text-3xl">
          {node.track.name}
        </h2>
        <p className="text-base text-muted-foreground">{node.track.artist}</p>
        <p className="font-mono text-[11px] text-muted-foreground">
          {node.track.genre}
          {node.track.year ? ` · ${node.track.year}` : ""}
        </p>
      </div>

      {path.length > 1 && (
        <ol className="flex max-w-lg flex-wrap items-center justify-center gap-1.5 text-xs text-muted-foreground">
          {path.map((item, index) => (
            <li key={item.id} className="flex items-center gap-1.5">
              {index > 0 && <span aria-hidden="true">→</span>}
              <span className={index === path.length - 1 ? "text-foreground font-medium" : undefined}>
                {item.track.name}
              </span>
            </li>
          ))}
        </ol>
      )}

      <div className="flex items-center gap-3">
        {onOpenDetails && (
          <Button variant="ghost" size="sm" onClick={onOpenDetails}>
            <Info className="size-4 mr-1.5" />
            Detalhes
          </Button>
        )}
        <Button variant="outline" onClick={onExpand} disabled={node.loading}>
          {node.loading ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Network aria-hidden="true" />}
          {childrenCount > 0 ? "Mais recomendações daqui" : "Recomendar a partir daqui"}
        </Button>
      </div>
    </div>
  )
}


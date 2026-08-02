"use client"

import { Loader2, Network, Pause, Play, Rewind, FastForward, ThumbsDown, ThumbsUp } from "lucide-react"
import { PreviewScrubber } from "@/components/preview-scrubber"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"

type Props = {
  node: GraphNode | null
  path: GraphNode[]
  childrenCount: number
  isPlaying: boolean
  currentTime: number
  duration: number
  onSeek: (time: number) => void
  onTogglePlay: () => void
  onFeedback: (feedback: "like" | "dislike") => void
  onExpand: () => void
}

export function TrackPanel({
  node,
  path,
  childrenCount,
  isPlaying,
  currentTime,
  duration,
  onSeek,
  onTogglePlay,
  onFeedback,
  onExpand,
}: Props) {
  if (!node) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border p-6 text-center">
        <Network className="size-6 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm text-muted-foreground text-pretty">
          Selecione um nó do grafo para ouvir o preview e avaliar a recomendação.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-3">
        <img
          src={node.track.artwork || "/placeholder.svg"}
          alt={`Capa de ${node.track.album || node.track.name}`}
          className="size-20 shrink-0 rounded-lg border border-border object-cover"
        />
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[10px] uppercase tracking-widest text-primary">
            {node.depth === 0 ? "Semente" : `Nível ${node.depth}`}
          </p>
          <h2 className="truncate text-base font-semibold leading-tight text-foreground">{node.track.name}</h2>
          <p className="truncate text-sm text-muted-foreground">{node.track.artist}</p>
          <p className="mt-1 truncate font-mono text-[11px] text-muted-foreground">
            {node.track.genre}
            {node.track.year ? ` · ${node.track.year}` : ""}
          </p>
        </div>
      </div>

      <PreviewScrubber
        trackId={node.track.trackId}
        currentTime={currentTime}
        duration={duration}
        onSeek={onSeek}
      />

      <div className="flex items-center gap-2">
        <Button
          size="icon"
          variant="outline"
          aria-label="Voltar 5 segundos"
          onClick={() => onSeek(Math.max(0, currentTime - 5))}
        >
          <Rewind aria-hidden="true" />
        </Button>
        <Button size="lg" className="flex-1" onClick={onTogglePlay}>
          {isPlaying ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
          {isPlaying ? "Pausar" : "Ouvir preview"}
        </Button>
        <Button
          size="icon"
          variant="outline"
          aria-label="Avançar 5 segundos"
          onClick={() => onSeek(Math.min(duration || 30, currentTime + 5))}
        >
          <FastForward aria-hidden="true" />
        </Button>
      </div>

      <Button size="lg" variant="outline" onClick={onExpand} disabled={node.loading}>
        {node.loading ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Network aria-hidden="true" />}
        {childrenCount > 0 ? "Mais recomendações" : "Recomendar a partir daqui"}
      </Button>

      <div className="grid grid-cols-2 gap-2">
        <Button
          size="lg"
          variant={node.feedback === "like" ? "default" : "outline"}
          onClick={() => onFeedback("like")}
          aria-pressed={node.feedback === "like"}
        >
          <ThumbsUp aria-hidden="true" />
          Gostei
        </Button>
        <Button
          size="lg"
          variant={node.feedback === "dislike" ? "destructive" : "outline"}
          onClick={() => onFeedback("dislike")}
          aria-pressed={node.feedback === "dislike"}
        >
          <ThumbsDown aria-hidden="true" />
          Não gostei
        </Button>
      </div>

      <div>
        <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Caminho no grafo</p>
        <ol className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
          {path.map((item, index) => (
            <li key={item.id} className="flex items-center gap-1">
              {index > 0 && <span aria-hidden="true">→</span>}
              <span className={index === path.length - 1 ? "text-foreground" : undefined}>{item.track.name}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}

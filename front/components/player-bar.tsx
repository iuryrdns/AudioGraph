"use client"

import {
  FastForward,
  Keyboard,
  Loader2,
  Pause,
  Play,
  Rewind,
  SkipBack,
  SkipForward,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Volume2,
  VolumeX,
} from "lucide-react"
import { PreviewScrubber } from "@/components/preview-scrubber"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"

type Props = {
  node: GraphNode
  isPlaying: boolean
  currentTime: number
  duration: number
  autoPlay: boolean
  hasPrevious: boolean
  loadingNext: boolean
  volume: number
  isMuted: boolean
  onSeek: (time: number) => void
  onTogglePlay: () => void
  onPrevious: () => void
  onNext: () => void
  onToggleAutoPlay: () => void
  onFeedback: (feedback: "like" | "dislike") => void
  onVolumeChange: (vol: number) => void
  onToggleMute: () => void
  onOpenShortcuts?: () => void
}

export function PlayerBar({
  node,
  isPlaying,
  currentTime,
  duration,
  autoPlay,
  hasPrevious,
  loadingNext,
  volume,
  isMuted,
  onSeek,
  onTogglePlay,
  onPrevious,
  onNext,
  onToggleAutoPlay,
  onFeedback,
  onVolumeChange,
  onToggleMute,
  onOpenShortcuts,
}: Props) {
  return (
    <footer className="shrink-0 border-t border-border bg-card/60 px-4 py-3 backdrop-blur md:px-6">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 lg:flex-row lg:items-center lg:gap-6">
        <div className="flex min-w-0 items-center gap-3 lg:w-64">
          <img
            src={node.track.artwork || "/placeholder.svg"}
            alt=""
            className="size-11 shrink-0 rounded-md border border-border object-cover"
          />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{node.track.name}</p>
            <p className="truncate font-mono text-[11px] text-muted-foreground">{node.track.artist}</p>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-2">
          <div className="flex items-center justify-center gap-1.5">
            <Button size="icon" variant="ghost" aria-label="Faixa anterior" disabled={!hasPrevious} onClick={onPrevious}>
              <SkipBack aria-hidden="true" />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Voltar 5 segundos"
              onClick={() => onSeek(Math.max(0, currentTime - 5))}
            >
              <Rewind aria-hidden="true" />
            </Button>
            <Button size="icon" className="size-11 rounded-full shadow-md" aria-label={isPlaying ? "Pausar" : "Tocar"} onClick={onTogglePlay}>
              {isPlaying ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
            </Button>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Avançar 5 segundos"
              onClick={() => onSeek(Math.min(duration || 30, currentTime + 5))}
            >
              <FastForward aria-hidden="true" />
            </Button>
            <Button size="icon" variant="ghost" aria-label="Próxima recomendação" onClick={onNext} disabled={loadingNext}>
              {loadingNext ? <Loader2 className="animate-spin" aria-hidden="true" /> : <SkipForward aria-hidden="true" />}
            </Button>
          </div>

          <PreviewScrubber
            variant="bar"
            trackId={node.track.trackId}
            currentTime={currentTime}
            duration={duration}
            onSeek={onSeek}
          />
        </div>

        <div className="flex items-center justify-center gap-2 lg:w-80 lg:justify-end">
          {/* Volume Control */}
          <div className="flex items-center gap-1.5 mr-2">
            <Button
              size="icon"
              variant="ghost"
              className="size-8"
              onClick={onToggleMute}
              title={isMuted ? "Desmutar" : "Mutar"}
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="size-4 text-muted-foreground" />
              ) : (
                <Volume2 className="size-4" />
              )}
            </Button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={isMuted ? 0 : volume}
              onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
              className="w-16 h-1 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
              aria-label="Volume"
            />
          </div>

          <Button
            variant={node.feedback === "like" ? "default" : "outline"}
            aria-pressed={node.feedback === "like"}
            size="sm"
            onClick={() => onFeedback("like")}
          >
            <ThumbsUp aria-hidden="true" />
            Gostei
          </Button>
          <Button
            variant={node.feedback === "dislike" ? "destructive" : "outline"}
            aria-pressed={node.feedback === "dislike"}
            size="sm"
            onClick={() => onFeedback("dislike")}
          >
            <ThumbsDown aria-hidden="true" />
            Não
          </Button>
          <Button
            size="icon"
            variant={autoPlay ? "secondary" : "ghost"}
            className="size-9"
            aria-label="Auto-play das recomendações"
            aria-pressed={autoPlay}
            title={autoPlay ? "Auto-play ligado" : "Auto-play desligado"}
            onClick={onToggleAutoPlay}
          >
            <Sparkles className={autoPlay ? "text-primary" : undefined} aria-hidden="true" />
          </Button>

          {onOpenShortcuts && (
            <Button
              size="icon"
              variant="ghost"
              className="size-9"
              title="Atalhos do teclado"
              onClick={onOpenShortcuts}
            >
              <Keyboard className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </footer>
  )
}

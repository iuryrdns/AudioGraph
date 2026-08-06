"use client"

import { ExternalLink, Disc, Calendar, Music, Sparkles, X } from "lucide-react"
import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"
import type { Track } from "@/lib/itunes"

type Props = {
  track: Track | null
  node?: GraphNode | null
  open: boolean
  onClose: () => void
  onSelectTrack?: (track: Track) => void
  onExpandNode?: (nodeId: string) => void
}

export function TrackDetailsDialog({
  track,
  node,
  open,
  onClose,
  onSelectTrack,
  onExpandNode,
}: Props) {
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open, onClose])

  if (!open || !track) return null

  const highResArtwork = track.artwork
    ? track.artwork.replace("300x300bb", "600x600bb")
    : "/placeholder.svg"

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-border bg-card shadow-2xl">
        <div className="relative h-48 w-full bg-muted">
          <img
            src={highResArtwork}
            alt={track.name}
            className="h-full w-full object-cover blur-sm opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-card to-transparent" />
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Fechar"
            className="absolute top-3 right-3 rounded-full bg-black/40 text-white backdrop-blur hover:bg-black/60"
          >
            <X className="size-4" />
          </Button>

          <div className="absolute -bottom-6 left-6 flex items-end gap-4">
            <img
              src={highResArtwork}
              alt={track.name}
              className="size-28 rounded-xl border-2 border-border object-cover shadow-xl bg-card"
            />
          </div>
        </div>

        <div className="pt-8 px-6 pb-6">
          <div className="flex flex-col gap-1">
            <span className="inline-flex w-fit items-center rounded-md bg-primary/10 px-2 py-0.5 font-mono text-[11px] font-medium text-primary">
              {track.genre}
            </span>
            <h2 className="text-xl font-bold text-foreground leading-snug">{track.name}</h2>
            <p className="text-sm font-medium text-muted-foreground">{track.artist}</p>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
            {track.album && (
              <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-2.5">
                <Disc className="size-4 text-primary shrink-0" />
                <div className="min-w-0">
                  <p className="font-mono text-[10px] uppercase text-muted-foreground">Álbum</p>
                  <p className="truncate font-medium text-foreground">{track.album}</p>
                </div>
              </div>
            )}
            {track.year && (
              <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 p-2.5">
                <Calendar className="size-4 text-primary shrink-0" />
                <div className="min-w-0">
                  <p className="font-mono text-[10px] uppercase text-muted-foreground">Lançamento</p>
                  <p className="truncate font-medium text-foreground">{track.year}</p>
                </div>
              </div>
            )}
          </div>

          {track.explanation && (
            <div className="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs">
              <div className="flex items-center justify-between font-mono text-[10px] uppercase text-primary mb-1">
                <span>Razão da Recomendação</span>
                {track.score !== undefined && (
                  <span className="rounded bg-primary/20 px-1.5 py-0.5 font-semibold">
                    Score: {(track.score).toFixed(2)}
                  </span>
                )}
              </div>
              <p className="text-foreground font-medium">{track.explanation}</p>
            </div>
          )}

          {node && (
            <div className="mt-3 rounded-lg border border-border bg-card p-3 font-mono text-xs">
              <div className="flex justify-between text-muted-foreground">
                <span>Nível da semente: #{node.depth}</span>
                <span>Feedback: {node.feedback === "like" ? "Curtido" : node.feedback === "dislike" ? "Rejeitado" : "Sem avaliação"}</span>
              </div>
            </div>
          )}

          <div className="mt-6 flex items-center justify-between gap-3 border-t border-border pt-4">
            <a
              href={`https://music.apple.com/search?term=${encodeURIComponent(`${track.name} ${track.artist}`)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <ExternalLink className="size-3.5" />
              Ver no Apple Music
            </a>

            <div className="flex items-center gap-2">
              {node && onExpandNode && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    onExpandNode(node.id)
                    onClose()
                  }}
                >
                  <Sparkles className="size-3.5 mr-1" />
                  Expandir
                </Button>
              )}
              {onSelectTrack && (
                <Button
                  size="sm"
                  onClick={() => {
                    onSelectTrack(track)
                    onClose()
                  }}
                >
                  <Music className="size-3.5 mr-1" />
                  Tocar Semente
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

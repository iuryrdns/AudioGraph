"use client"

import { Info, ThumbsUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { GraphNode } from "@/lib/graph"

type Props = {
  queue: GraphNode[]
  onPick: (id: string) => void
  onOpenDetails?: (node: GraphNode) => void
}

export function UpNext({ queue, onPick, onOpenDetails }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        A seguir · {queue.length} faixas
      </p>
      {queue.length === 0 ? (
        <p className="text-xs text-muted-foreground text-pretty">
          A fila terminou. Curta uma faixa ou peça mais recomendações para continuar.
        </p>
      ) : (
        <ul className="flex flex-col gap-0.5">
          {queue.slice(0, 12).map((node, index) => (
            <li key={`${node.id}-${index}`} className="group relative flex items-center">
              <button
                type="button"
                onClick={() => onPick(node.id)}
                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-muted"
              >
                <span className="w-4 shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">
                  {index + 1}
                </span>
                <img src={node.track.artwork || "/placeholder.svg"} alt="" className="size-9 rounded object-cover" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium text-foreground">{node.track.name}</span>
                  <span className="block truncate font-mono text-[10px] text-muted-foreground">
                    {node.track.artist}
                  </span>
                </span>
                {node.feedback === "like" && <ThumbsUp className="size-3.5 shrink-0 text-primary" aria-hidden="true" />}
              </button>
              {onOpenDetails && (
                <Button
                  size="icon"
                  variant="ghost"
                  className="absolute right-1 size-7 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Ver detalhes"
                  onClick={(e) => {
                    e.stopPropagation()
                    onOpenDetails(node)
                  }}
                >
                  <Info className="size-3.5" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

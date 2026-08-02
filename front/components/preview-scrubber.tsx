"use client"

import { useCallback, useMemo, useRef, useState } from "react"

type Props = {
  trackId: number
  currentTime: number
  duration: number
  onSeek: (time: number) => void
  /** "bar" deixa a onda mais baixa e esconde a dica, para uso na barra do player. */
  variant?: "full" | "bar"
}

const BARS = 56

/** Gera uma silhueta estável por faixa (previews não expõem CORS para decodificar o áudio real). */
function useWaveform(trackId: number) {
  return useMemo(() => {
    let seed = trackId || 1
    const random = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296
      return seed / 4294967296
    }
    return Array.from({ length: BARS }, (_, index) => {
      const envelope = Math.sin((index / (BARS - 1)) * Math.PI) * 0.55 + 0.45
      return Math.min(1, Math.max(0.16, (0.35 + random() * 0.65) * envelope))
    })
  }, [trackId])
}

function formatTime(seconds: number) {
  const safe = Number.isFinite(seconds) && seconds > 0 ? Math.floor(seconds) : 0
  return `${Math.floor(safe / 60)}:${String(safe % 60).padStart(2, "0")}`
}

export function PreviewScrubber({ trackId, currentTime, duration, onSeek, variant = "full" }: Props) {
  const bars = useWaveform(trackId)
  const trackRef = useRef<HTMLDivElement>(null)
  const [dragTime, setDragTime] = useState<number | null>(null)

  const total = duration > 0 ? duration : 30
  const displayTime = dragTime ?? Math.min(currentTime, total)
  const progress = Math.min(1, Math.max(0, displayTime / total))

  const timeFromEvent = useCallback(
    (clientX: number) => {
      const rect = trackRef.current?.getBoundingClientRect()
      if (!rect || rect.width === 0) return 0
      return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width)) * total
    },
    [total],
  )

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId)
      const time = timeFromEvent(event.clientX)
      setDragTime(time)
      onSeek(time)
    },
    [onSeek, timeFromEvent],
  )

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (dragTime === null) return
      const time = timeFromEvent(event.clientX)
      setDragTime(time)
      onSeek(time)
    },
    [dragTime, onSeek, timeFromEvent],
  )

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      const step = event.shiftKey ? 5 : 1
      const actions: Record<string, number | undefined> = {
        ArrowLeft: Math.max(0, displayTime - step),
        ArrowRight: Math.min(total, displayTime + step),
        Home: 0,
        End: total,
      }
      const next = actions[event.key]
      if (next === undefined) return
      event.preventDefault()
      onSeek(next)
    },
    [displayTime, onSeek, total],
  )

  return (
    <div className="flex flex-col gap-1.5">
      <div
        ref={trackRef}
        role="slider"
        tabIndex={0}
        aria-label="Posição do preview"
        aria-valuemin={0}
        aria-valuemax={Math.round(total)}
        aria-valuenow={Math.round(displayTime)}
        aria-valuetext={`${formatTime(displayTime)} de ${formatTime(total)}`}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={() => setDragTime(null)}
        onPointerCancel={() => setDragTime(null)}
        onKeyDown={handleKeyDown}
        className={`flex cursor-pointer touch-none items-center gap-px rounded-lg bg-muted/40 px-2 outline-none ring-offset-2 ring-offset-background focus-visible:ring-2 focus-visible:ring-ring ${
          variant === "bar" ? "h-9" : "h-16"
        }`}
      >
        {bars.map((height, index) => {
          const played = index / (BARS - 1) <= progress
          return (
            <span
              key={index}
              aria-hidden="true"
              className={`flex-1 rounded-full transition-colors ${played ? "bg-primary" : "bg-muted-foreground/35"}`}
              style={{ height: `${Math.round(height * 100)}%` }}
            />
          )
        })}
      </div>
      <div className="flex items-baseline justify-between gap-3 font-mono text-[10px] text-muted-foreground">
        <span className="tabular-nums text-foreground">{formatTime(displayTime)}</span>
        {variant === "full" && <span className="truncate">arraste para escolher o trecho</span>}
        <span className="tabular-nums">{formatTime(total)}</span>
      </div>
    </div>
  )
}

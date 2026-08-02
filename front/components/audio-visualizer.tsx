"use client"

import { useEffect, useState } from "react"

type Props = {
  isPlaying: boolean
  barCount?: number
  className?: string
}

export function AudioVisualizer({ isPlaying, barCount = 16, className = "" }: Props) {
  const [heights, setHeights] = useState<number[]>(() =>
    Array.from({ length: barCount }, () => 15)
  )

  useEffect(() => {
    if (!isPlaying) {
      setHeights(Array.from({ length: barCount }, () => 12))
      return
    }

    const interval = setInterval(() => {
      setHeights(
        Array.from({ length: barCount }, () =>
          Math.floor(Math.random() * 75 + 20)
        )
      )
    }, 120)

    return () => clearInterval(interval)
  }, [isPlaying, barCount])

  return (
    <div className={`flex items-end justify-center gap-[3px] ${className}`} aria-hidden="true">
      {heights.map((height, i) => (
        <span
          key={i}
          className="w-1 rounded-t bg-primary transition-all duration-150 ease-in-out opacity-80"
          style={{
            height: `${height}%`,
            minHeight: "4px",
          }}
        />
      ))}
    </div>
  )
}

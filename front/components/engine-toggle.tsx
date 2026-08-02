"use client"

import { Cpu, Globe, Server } from "lucide-react"
import { useEffect, useState } from "react"

export type EngineMode = "itunes" | "python"

type Props = {
  mode: EngineMode
  onChange: (mode: EngineMode) => void
}

export function EngineToggle({ mode, onChange }: Props) {
  const [pythonOnline, setPythonOnline] = useState<boolean | null>(null)

  useEffect(() => {
    let active = true
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/health", { method: "GET" })
        if (active) setPythonOnline(res.ok)
      } catch {
        if (active) setPythonOnline(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  return (
    <div className="flex items-center gap-1 rounded-xl border border-border bg-card p-1 text-xs">
      <button
        type="button"
        onClick={() => onChange("itunes")}
        className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium transition-all ${
          mode === "itunes"
            ? "bg-primary text-primary-foreground shadow-xs"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <Globe className="size-3.5" />
        <span>iTunes Live</span>
      </button>

      <button
        type="button"
        onClick={() => onChange("python")}
        className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium transition-all ${
          mode === "python"
            ? "bg-primary text-primary-foreground shadow-xs"
            : "text-muted-foreground hover:text-foreground"
        }`}
      >
        <div className="relative flex items-center justify-center">
          <Cpu className="size-3.5" />
          <span
            className={`absolute -top-0.5 -right-0.5 size-1.5 rounded-full ${
              pythonOnline === true
                ? "bg-emerald-400 animate-pulse"
                : pythonOnline === false
                ? "bg-amber-400"
                : "bg-muted-foreground"
            }`}
            title={
              pythonOnline === true
                ? "Servidor Python Online (Porta 8000)"
                : "Servidor Python Offline (Inicie `uvicorn src.api.server:app`)"
            }
          />
        </div>
        <span>Python Engine</span>
      </button>
    </div>
  )
}

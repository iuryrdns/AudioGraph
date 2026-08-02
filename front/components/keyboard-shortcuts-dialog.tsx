"use client"

import { Keyboard, X } from "lucide-react"
import { useEffect } from "react"
import { Button } from "@/components/ui/button"

type Props = {
  open: boolean
  onClose: () => void
}

const SHORTCUTS = [
  { key: "Espaço", desc: "Tocar / Pausar reprodução" },
  { key: "Seta Direita", desc: "Próxima recomendação" },
  { key: "Seta Esquerda", desc: "Ir para a faixa anterior" },
  { key: "L", desc: "Dar Gostei na faixa atual" },
  { key: "D", desc: "Descartar / Não Gostei na faixa atual" },
  { key: "M", desc: "Mutar / Desmutar áudio" },
]

export function KeyboardShortcutsDialog({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border pb-4">
          <div className="flex items-center gap-2 text-foreground">
            <Keyboard className="size-5 text-primary" aria-hidden="true" />
            <h2 className="text-lg font-semibold">Atalhos do Teclado</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Fechar">
            <X className="size-4" />
          </Button>
        </div>

        <ul className="mt-4 flex flex-col gap-3">
          {SHORTCUTS.map((item) => (
            <li key={item.key} className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{item.desc}</span>
              <kbd className="rounded-md border border-border bg-muted px-2.5 py-1 font-mono text-xs font-semibold text-foreground shadow-xs">
                {item.key}
              </kbd>
            </li>
          ))}
        </ul>

        <div className="mt-6 flex justify-end">
          <Button onClick={onClose}>Entendi</Button>
        </div>
      </div>
    </div>
  )
}

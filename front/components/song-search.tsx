"use client"

import { Loader2, Search } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import type { Track } from "@/lib/itunes"

type Props = {
  onPick: (track: Track) => void
  disabled?: boolean
  engineMode?: "itunes" | "python"
}

export function SongSearch({ onPick, disabled, engineMode = "itunes" }: Props) {
  const [term, setTerm] = useState("")
  const [results, setResults] = useState<Track[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [needsFallback, setNeedsFallback] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const runSearch = async (query: string, allowFallback: boolean) => {
    setLoading(true)
    try {
      const res = await fetch(
        `/api/search?q=${encodeURIComponent(query)}&engine=${engineMode}${allowFallback ? "&allowFallback=1" : ""}`,
      )
      const data = (await res.json()) as { results: Track[]; source?: "python" | "itunes"; needsFallback?: boolean }
      setResults(data.results ?? [])
      setNeedsFallback(Boolean(data.needsFallback))
      setOpen(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const query = term.trim()
    setNeedsFallback(false)
    if (query.length < 2) {
      setResults([])
      return
    }
    let active = true
    const timeout = setTimeout(() => {
      if (active) runSearch(query, false)
    }, 350)
    return () => {
      active = false
      clearTimeout(timeout)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [term, engineMode])


  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [])

  const pick = (track: Track) => {
    onPick(track)
    setTerm("")
    setResults([])
    setOpen(false)
  }

  const QUICK_GENRES = ["Synthwave", "Pop", "Rock", "Indie", "Jazz", "Electronic", "Classical", "Lo-Fi"]

  const pickGenre = (genre: string) => {
    setTerm(genre)
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 focus-within:border-primary/60 focus-within:ring-3 focus-within:ring-ring/30">
        {loading ? (
          <Loader2 className="size-4 animate-spin text-primary" aria-hidden="true" />
        ) : (
          <Search className="size-4 text-muted-foreground" aria-hidden="true" />
        )}
        <input
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing || event.keyCode === 229) return
            if (event.key === "Enter" && results[0]) pick(results[0])
            if (event.key === "Escape") setOpen(false)
          }}
          disabled={disabled}
          placeholder="Digite uma música ou artista (ex: Blinding Lights)"
          aria-label="Buscar música"
          className="h-6 w-full bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground"
        />
      </div>

      {open && (
        <div className="absolute z-30 mt-2 max-h-80 w-full overflow-y-auto rounded-xl border border-border bg-popover p-2 shadow-2xl">
          {needsFallback && (
            <div className="mb-2 flex flex-col gap-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2.5 py-2 text-[11px] leading-snug text-amber-400">
              <span>
                O motor Python não encontrou nada no grafo pra "{term}". Quer buscar no iTunes em
                vez disso? (essas faixas ficam fora do grafo de recomendação)
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => runSearch(term.trim(), true)}
                  className="rounded-md border border-amber-500/50 bg-amber-500/20 px-2 py-1 text-[11px] font-medium text-amber-300 hover:bg-amber-500/30"
                >
                  Buscar no iTunes
                </button>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded-md border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
          {term.trim().length < 2 ? (
            <div className="flex flex-col gap-2 p-2">
              <p className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Gêneros em destaque
              </p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_GENRES.map((genre) => (
                  <button
                    key={genre}
                    type="button"
                    onClick={() => pickGenre(genre)}
                    className="rounded-lg border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted hover:border-primary/50 transition-colors"
                  >
                    {genre}
                  </button>
                ))}
              </div>
            </div>
          ) : results.length > 0 ? (
            <ul className="flex flex-col gap-0.5">
              {results.map((track) => (
                <li key={track.trackId}>
                  <button
                    type="button"
                    onClick={() => pick(track)}
                    className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-muted"
                  >
                    <img
                      src={track.artwork || "/placeholder.svg"}
                      alt=""
                      className="size-10 shrink-0 rounded-md object-cover"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-foreground">{track.name}</span>
                      <span className="block truncate font-mono text-[11px] text-muted-foreground">
                        {track.artist} · {track.genre}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : !loading && !needsFallback ? (
            <p className="p-3 text-center text-xs text-muted-foreground">Nenhuma música encontrada para "{term}"</p>
          ) : null}
        </div>
      )}
    </div>
  )
}


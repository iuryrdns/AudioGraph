"use client"

import { AudioLines, Download, ListMusic, Network, RotateCcw, ThumbsDown, ThumbsUp } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { EngineToggle, type EngineMode } from "@/components/engine-toggle"
import { NowPlaying } from "@/components/now-playing"
import { PlayerBar } from "@/components/player-bar"
import { RecommendationGraph } from "@/components/recommendation-graph"
import { SongSearch } from "@/components/song-search"
import { UpNext } from "@/components/up-next"
import { Button } from "@/components/ui/button"
import { KeyboardShortcutsDialog } from "@/components/keyboard-shortcuts-dialog"
import { TrackDetailsDialog } from "@/components/track-details-dialog"
import { buildFeedback, buildQueue, type GraphNode } from "@/lib/graph"
import type { Track } from "@/lib/itunes"

export function GraphExplorer() {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>([])
  const [autoPlay, setAutoPlay] = useState(true)
  const [showGraph, setShowGraph] = useState(false)
  const [loadingNext, setLoadingNext] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(30)

  // Engine Mode Selection ("itunes" or "python")
  const [engineMode, setEngineMode] = useState<EngineMode>("itunes")

  // Volume & Audio controls
  const [volume, setVolume] = useState(0.8)
  const [isMuted, setIsMuted] = useState(false)

  // Dialog states
  const [shortcutsOpen, setShortcutsOpen] = useState(false)
  const [detailsNode, setDetailsNode] = useState<GraphNode | null>(null)

  const audioRef = useRef<HTMLAudioElement>(null)
  const pendingSeekRef = useRef<number | null>(null)
  const nodesRef = useRef<GraphNode[]>([])
  const historyRef = useRef<string[]>([])
  const selectedIdRef = useRef<string | null>(null)
  const engineModeRef = useRef<EngineMode>("itunes")
  nodesRef.current = nodes
  historyRef.current = history
  selectedIdRef.current = selectedId
  engineModeRef.current = engineMode

  const selected = nodes.find((node) => node.id === selectedId) ?? null

  const path = useMemo(() => {
    const result: GraphNode[] = []
    let current = selected
    while (current) {
      result.unshift(current)
      const parentId: string | null = current.parentId
      current = parentId ? (nodes.find((node) => node.id === parentId) ?? null) : null
    }
    return result
  }, [selected, nodes])

  const queue = useMemo(() => buildQueue(nodes, selectedId, new Set(history)), [nodes, selectedId, history])

  const play = useCallback((node: GraphNode, startAt = 0, remember = true) => {
    const audio = audioRef.current
    if (!audio) return
    if (remember) {
      const next = [...historyRef.current.filter((id) => id !== node.id), node.id]
      historyRef.current = next
      setHistory(next)
    }

    const pUrl = node.track.previewUrl || ""
    const targetUrl = pUrl.startsWith("http")
      ? `/api/audio?url=${encodeURIComponent(pUrl)}&name=${encodeURIComponent(node.track.name)}&artist=${encodeURIComponent(node.track.artist)}`
      : `/api/audio?name=${encodeURIComponent(node.track.name)}&artist=${encodeURIComponent(node.track.artist)}`

    if (audio.src !== window.location.origin + targetUrl && audio.currentSrc !== window.location.origin + targetUrl) {
      audio.pause()
      audio.src = targetUrl
      setDuration(30)
      pendingSeekRef.current = startAt
    } else {
      audio.currentTime = startAt
    }
    setCurrentTime(startAt)
    audio.volume = isMuted ? 0 : volume
    audio
      .play()
      .then(() => setPlayingId(node.id))
      .catch(() => setPlayingId(null))
  }, [volume, isMuted])


  const stop = useCallback(() => {
    audioRef.current?.pause()
    setPlayingId(null)
  }, [])

  const seek = useCallback(
    (time: number) => {
      const audio = audioRef.current
      if (!audio || !selected) return
      audio.currentTime = time
      setCurrentTime(time)
    },
    [selected],
  )

  const expand = useCallback(async (id: string, count = 4) => {
    const current = nodesRef.current
    const node = current.find((item) => item.id === id)
    if (!node || node.loading) return

    const withLoading = current.map((item) => (item.id === id ? { ...item, loading: true } : item))
    nodesRef.current = withLoading
    setNodes(withLoading)

    try {
      const res = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          engine: engineModeRef.current,
          seed: {
            trackId: node.track.trackId,
            name: node.track.name,
            artist: node.track.artist,
            artistId: node.track.artistId,
            genre: node.track.genre,
          },
          feedback: buildFeedback(current),
          exclude: current.map((item) => item.track.trackId),
          count,
        }),
      })
      const data = (await res.json()) as { results: Track[] }
      const existingTrackIds = new Set(nodesRef.current.map((item) => item.track.trackId))
      const existingNodeIds = new Set(nodesRef.current.map((item) => item.id))
      const children: GraphNode[] = []
      for (const track of data.results ?? []) {
        const nodeId = `${id}-${track.trackId}`
        if (!existingTrackIds.has(track.trackId) && !existingNodeIds.has(nodeId)) {
          existingTrackIds.add(track.trackId)
          existingNodeIds.add(nodeId)
          children.push({
            id: nodeId,
            track,
            parentId: id,
            depth: node.depth + 1,
            feedback: null,
            expanded: false,
            loading: false,
          })
        }
      }
      const next = [
        ...nodesRef.current.map((item) => (item.id === id ? { ...item, loading: false, expanded: true } : item)),
        ...children,
      ]
      nodesRef.current = next
      setNodes(next)
    } catch {
      const next = nodesRef.current.map((item) => (item.id === id ? { ...item, loading: false } : item))
      nodesRef.current = next
      setNodes(next)
    }
  }, [])

  const advance = useCallback(async () => {
    const currentId = selectedIdRef.current
    let next = buildQueue(nodesRef.current, currentId, new Set(historyRef.current))[0]

    if (!next && currentId) {
      setLoadingNext(true)
      await expand(currentId, 3)
      setLoadingNext(false)
      next = buildQueue(nodesRef.current, currentId, new Set(historyRef.current))[0]
    }
    if (!next) {
      setPlayingId(null)
      return
    }
    setSelectedId(next.id)
    selectedIdRef.current = next.id
    play(next)
  }, [expand, play])

  const previous = useCallback(() => {
    const trimmed = historyRef.current.slice(0, -1)
    const previousId = trimmed[trimmed.length - 1]
    if (!previousId) return
    historyRef.current = trimmed
    setHistory(trimmed)
    const node = nodesRef.current.find((item) => item.id === previousId)
    if (!node) return
    setSelectedId(previousId)
    selectedIdRef.current = previousId
    play(node, 0, false)
  }, [play])

  const start = useCallback(
    (track: Track) => {
      stop()
      const root: GraphNode = {
        id: `root-${track.trackId}`,
        track,
        parentId: null,
        depth: 0,
        feedback: null,
        expanded: false,
        loading: false,
      }
      nodesRef.current = [root]
      historyRef.current = []
      setNodes([root])
      setHistory([])
      setSelectedId(root.id)
      selectedIdRef.current = root.id
      play(root)
      void expand(root.id, 5)
    },
    [expand, play, stop],
  )

  const select = useCallback(
    (id: string) => {
      setSelectedId(id)
      selectedIdRef.current = id
      const node = nodesRef.current.find((item) => item.id === id)
      if (!node) return
      play(node)
    },
    [play],
  )

  const applyFeedback = useCallback(
    (id: string, feedback: "like" | "dislike") => {
      const node = nodesRef.current.find((item) => item.id === id)
      if (!node) return
      const next = node.feedback === feedback ? null : feedback
      const updated = nodesRef.current.map((item) => (item.id === id ? { ...item, feedback: next } : item))
      nodesRef.current = updated
      setNodes(updated)

      if (next === "like" && !node.expanded) {
        void expand(id, 3)
      }
      if (next === "dislike") {
        if (node.parentId) void expand(node.parentId, 1)
        if (id === selectedIdRef.current) void advance()
      }
    },
    [advance, expand],
  )

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement
      if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return

      if (e.code === "Space") {
        e.preventDefault()
        if (selected) {
          if (playingId === selected.id) stop()
          else play(selected, audioRef.current?.currentTime || 0, false)
        }
      } else if (e.code === "ArrowRight") {
        e.preventDefault()
        void advance()
      } else if (e.code === "ArrowLeft") {
        e.preventDefault()
        previous()
      } else if (e.key.toLowerCase() === "l" && selected) {
        e.preventDefault()
        applyFeedback(selected.id, "like")
      } else if ((e.key.toLowerCase() === "d" || e.key.toLowerCase() === "x") && selected) {
        e.preventDefault()
        applyFeedback(selected.id, "dislike")
      } else if (e.key.toLowerCase() === "m") {
        e.preventDefault()
        setIsMuted((prev) => !prev)
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [selected, playingId, play, stop, advance, previous, applyFeedback])

  // Sync Volume to Audio element
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume
    }
  }, [volume, isMuted])

  const stats = useMemo(() => {
    const liked = nodes.filter((node) => node.feedback === "like")
    const disliked = nodes.filter((node) => node.feedback === "dislike")
    const genreCount = new Map<string, number>()
    for (const node of liked) genreCount.set(node.track.genre, (genreCount.get(node.track.genre) ?? 0) + 1)
    const topGenres = Array.from(genreCount.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
    return { liked, disliked, topGenres }
  }, [nodes])

  const exportLikedPlaylist = useCallback(() => {
    if (stats.liked.length === 0) return
    const lines = ["#EXTM3U"]
    stats.liked.forEach((n) => {
      lines.push(`#EXTINF:-1,${n.track.artist} - ${n.track.name}`)
      lines.push(n.track.previewUrl)
    })
    const content = lines.join("\n")
    const blob = new Blob([content], { type: "audio/x-mpegurl" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "audiograph-liked-playlist.m3u"
    a.click()
    URL.revokeObjectURL(url)
  }, [stats.liked])

  const started = nodes.length > 0

  return (
    <div className="flex h-dvh flex-col bg-background" suppressHydrationWarning>
      <header className="flex shrink-0 flex-col gap-3 border-b border-border px-4 py-3 md:flex-row md:items-center md:gap-6 md:px-6" suppressHydrationWarning>
        <div className="flex items-center gap-2">
          <AudioLines className="size-5 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-sm font-semibold leading-none text-foreground">AudioGraph-AI</h1>
            <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              rádio de recomendação inteligente
            </p>
          </div>
        </div>

        <div className="flex flex-1 flex-col sm:flex-row items-center gap-3 md:max-w-xl">
          <div className="flex-1 w-full">
            <SongSearch onPick={start} engineMode={engineMode} />
          </div>
          <EngineToggle mode={engineMode} onChange={setEngineMode} />
        </div>

        {started && (
          <div className="flex items-center gap-2 md:ml-auto">
            <Button
              variant={showGraph ? "default" : "outline"}
              aria-pressed={showGraph}
              onClick={() => setShowGraph((value) => !value)}
            >
              {showGraph ? <ListMusic aria-hidden="true" /> : <Network aria-hidden="true" />}
              {showGraph ? "Ver player" : "Ver grafo"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                stop()
                nodesRef.current = []
                historyRef.current = []
                setNodes([])
                setHistory([])
                setSelectedId(null)
                setShowGraph(false)
              }}
            >
              <RotateCcw aria-hidden="true" />
              Reiniciar
            </Button>
          </div>
        )}
      </header>

      <main className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <section className="relative min-h-0 flex-1" aria-label={showGraph ? "Grafo de recomendações" : "Tocando agora"}>
          {!started || !selected ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
              <AudioLines className="size-8 text-primary" aria-hidden="true" />
              <h2 className="text-2xl font-semibold text-foreground text-balance">
                Busque uma música ou gênero para começar
              </h2>
              <p className="max-w-sm text-sm text-muted-foreground text-pretty">
                A faixa escolhida vira a semente da rádio. Quando o preview acaba, a próxima recomendação entra sozinha
                — curta ou descarte para afinar a fila.
              </p>
            </div>
          ) : showGraph ? (
            <RecommendationGraph
              nodes={nodes}
              selectedId={selectedId}
              playingId={playingId}
              onSelect={select}
              onExpand={(id) => void expand(id, 3)}
              onOpenDetails={(node) => setDetailsNode(node)}
            />
          ) : (
            <NowPlaying
              node={selected}
              path={path}
              isPlaying={playingId === selected.id}
              childrenCount={nodes.filter((node) => node.parentId === selected.id).length}
              onExpand={() => void expand(selected.id, 3)}
              onOpenDetails={() => setDetailsNode(selected)}
            />
          )}
        </section>

        {started && (
          <aside
            className="flex w-full shrink-0 flex-col gap-5 overflow-y-auto border-t border-border p-4 lg:w-80 lg:border-l lg:border-t-0 lg:p-5"
            aria-label="Fila e perfil"
          >
            <UpNext
              queue={queue}
              onPick={select}
              onOpenDetails={(node) => setDetailsNode(node)}
            />

            <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4">
              <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">Seu perfil</p>
              <div className="flex gap-4 text-sm">
                <span className="flex items-center gap-1.5 text-primary">
                  <ThumbsUp className="size-4" aria-hidden="true" />
                  {stats.liked.length} curtidas
                </span>
                <span className="flex items-center gap-1.5 text-destructive">
                  <ThumbsDown className="size-4" aria-hidden="true" />
                  {stats.disliked.length} descartes
                </span>
              </div>
              {stats.topGenres.length > 0 && (
                <ul className="flex flex-col gap-1.5">
                  {stats.topGenres.map(([genre, count]) => (
                    <li key={genre} className="flex items-center gap-2">
                      <span className="w-24 shrink-0 truncate font-mono text-[11px] text-muted-foreground">
                        {genre}
                      </span>
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                        <span
                          className="block h-full rounded-full bg-primary"
                          style={{ width: `${(count / stats.topGenres[0][1]) * 100}%` }}
                        />
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-muted-foreground text-pretty">
                {nodes.length} faixas descobertas. Suas avaliações pesam gêneros e artistas nas próximas buscas.
              </p>
            </div>

            {stats.liked.length > 0 && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <p className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
                    Playlist curtida
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-1.5 text-[11px]"
                    onClick={exportLikedPlaylist}
                    title="Exportar como playlist .M3U"
                  >
                    <Download className="size-3 mr-1" />
                    Exportar
                  </Button>
                </div>
                <ul className="flex flex-col gap-0.5">
                  {stats.liked.map((node, index) => (
                    <li key={`${node.id}-${index}`}>
                      <button
                        type="button"
                        onClick={() => select(node.id)}
                        className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-muted"
                      >
                        <img
                          src={node.track.artwork || "/placeholder.svg"}
                          alt=""
                          className="size-9 rounded object-cover"
                        />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-xs font-medium text-foreground">{node.track.name}</span>
                          <span className="block truncate font-mono text-[10px] text-muted-foreground">
                            {node.track.artist}
                          </span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </aside>
        )}
      </main>

      {selected && (
        <PlayerBar
          node={selected}
          isPlaying={playingId === selected.id}
          currentTime={audioRef.current?.currentSrc === selected.track.previewUrl ? currentTime : 0}
          duration={duration}
          autoPlay={autoPlay}
          hasPrevious={history.length > 1}
          loadingNext={loadingNext}
          volume={volume}
          isMuted={isMuted}
          onSeek={seek}
          onTogglePlay={() => {
            if (playingId === selected.id) stop()
            else play(selected, audioRef.current?.currentSrc === selected.track.previewUrl ? currentTime : 0, false)
          }}
          onPrevious={previous}
          onNext={() => void advance()}
          onToggleAutoPlay={() => setAutoPlay((value) => !value)}
          onFeedback={(feedback) => applyFeedback(selected.id, feedback)}
          onVolumeChange={(v) => setVolume(v)}
          onToggleMute={() => setIsMuted((prev) => !prev)}
          onOpenShortcuts={() => setShortcutsOpen(true)}
        />
      )}

      {/* Keyboard Shortcuts Dialog */}
      <KeyboardShortcutsDialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />

      {/* Track Details Dialog */}
      <TrackDetailsDialog
        track={detailsNode?.track ?? null}
        node={detailsNode}
        open={!!detailsNode}
        onClose={() => setDetailsNode(null)}
        onSelectTrack={start}
        onExpandNode={(id) => void expand(id, 3)}
      />

      <audio
        ref={audioRef}
        className="sr-only"
        onTimeUpdate={(event) => setCurrentTime(event.currentTarget.currentTime)}
        onLoadedMetadata={(event) => {
          const audio = event.currentTarget
          if (Number.isFinite(audio.duration) && audio.duration > 0) setDuration(audio.duration)
          if (pendingSeekRef.current !== null) {
            audio.currentTime = pendingSeekRef.current
            pendingSeekRef.current = null
          }
        }}
        onEnded={() => {
          setPlayingId(null)
          if (autoPlay) void advance()
        }}
      />
    </div>
  )
}

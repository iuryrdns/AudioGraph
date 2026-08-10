import { dedupe, itunes, normalize, type Track } from "@/lib/itunes"

const JUNK = /kidz bop|karaoke|tribute|instrumental version|made famous|8-bit|lullaby|cover band/i

type Body = {
  engine?: "itunes" | "python"
  allowFallback?: boolean
  seed: { trackId: number | string; name: string; artist: string; artistId: number | string; genre: string }
  feedback?: {
    likedArtists?: string[]
    likedGenres?: string[]
    dislikedArtists?: string[]
    dislikedGenres?: string[]
  }
  exclude?: (number | string)[]
  count?: number
}

export async function POST(request: Request) {
  const body = (await request.json()) as Body
  const seed = body.seed
  if (!seed?.name) return Response.json({ results: [] }, { status: 400 })

  // If engine mode is "python", try querying local Python FastAPI server first
  if (body.engine === "python" && !body.allowFallback) {
    try {
      const pythonBase = process.env.PYTHON_ENGINE_URL || "http://127.0.0.1:8000"
      const pyRes = await fetch(`${pythonBase}/api/py/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (pyRes.ok) {
        const pyData = await pyRes.json()
        if (pyData.results && pyData.results.length > 0) {
          return Response.json({ ...pyData, source: "python" })
        }
      }
    } catch {
      // Python backend offline.
    }
    // Python engine found nothing (or is offline). Don't silently run the
    // iTunes algorithm — tell the frontend so it can ask the user first.
    // The frontend re-POSTs with allowFallback:true if the user says yes.
    return Response.json({ results: [], source: "python", needsFallback: true })
  }

  const fb = body.feedback ?? {}
  const likedArtists = (fb.likedArtists ?? []).map((s) => s.toLowerCase())
  const likedGenres = (fb.likedGenres ?? []).map((s) => s.toLowerCase())
  const dislikedArtists = (fb.dislikedArtists ?? []).map((s) => s.toLowerCase())
  const dislikedGenres = (fb.dislikedGenres ?? []).map((s) => s.toLowerCase())
  const exclude = new Set((body.exclude ?? []).map(String))
  const count = Math.min(Math.max(body.count ?? 4, 1), 6)

  const queries: Promise<Track[]>[] = [
    itunes("/lookup", {
      id: String(seed.artistId || 0),
      entity: "song",
      limit: "20",
    }).then((r) => normalize(r)),
    itunes("/search", { term: seed.artist, entity: "song", media: "music", limit: "25" }).then((r) => normalize(r)),
    itunes("/search", { term: seed.genre, entity: "song", media: "music", limit: "25" }).then((r) => normalize(r)),
    itunes("/search", {
      term: `${seed.genre} ${seed.name.split("(")[0]}`,
      entity: "song",
      media: "music",
      limit: "20",
    }).then((r) => normalize(r)),
  ]

  for (const artist of (fb.likedArtists ?? []).slice(-2)) {
    queries.push(
      itunes("/search", { term: artist, entity: "song", media: "music", limit: "15" }).then((r) => normalize(r)),
    )
  }
  for (const genre of Array.from(new Set(fb.likedGenres ?? [])).slice(-2)) {
    queries.push(
      itunes("/search", { term: genre, entity: "song", media: "music", limit: "15" }).then((r) => normalize(r)),
    )
  }

  const pools = await Promise.all(queries)
  const candidates = dedupe(pools.flat()).filter(
    (t) =>
      !exclude.has(String(t.trackId)) &&
      String(t.trackId) !== String(seed.trackId) &&
      t.name.toLowerCase() !== seed.name.toLowerCase() &&
      !JUNK.test(t.artist) &&
      !JUNK.test(t.album),
  )

  const scored = candidates.map((track) => {
    const artist = track.artist.toLowerCase()
    const genre = track.genre.toLowerCase()
    let score = 0
    if (genre === seed.genre.toLowerCase()) score += 3
    if (likedGenres.includes(genre)) score += 2.5
    if (likedArtists.includes(artist)) score += 2
    if (dislikedGenres.includes(genre)) score -= 4
    if (dislikedArtists.includes(artist)) score -= 8
    if (artist === seed.artist.toLowerCase()) score -= 1.5
    score += Math.random() * 1.8
    return { track, score }
  })

  scored.sort((a, b) => b.score - a.score)

  const usedArtists = new Set<string>()
  const results: Track[] = []
  for (const { track } of scored) {
    const artist = track.artist.toLowerCase()
    if (usedArtists.has(artist)) continue
    usedArtists.add(artist)
    results.push(track)
    if (results.length >= count) break
  }

  // `source` tells the UI which engine actually answered — lets it warn the
  // user when they asked for "python" but got the iTunes text-scoring
  // algorithm instead (e.g. Python server offline, or seed not in the graph).
  return Response.json({ results, source: "itunes" })
}

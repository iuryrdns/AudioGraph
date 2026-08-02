export type Track = {
  trackId: number | string
  name: string
  artist: string
  artistId: number | string
  genre: string
  artwork: string
  previewUrl: string
  album: string
  year: string
  explanation?: string
  score?: number
}

type RawResult = {
  wrapperType?: string
  kind?: string
  trackId?: number
  trackName?: string
  artistName?: string
  artistId?: number
  primaryGenreName?: string
  artworkUrl100?: string
  previewUrl?: string
  collectionName?: string
  releaseDate?: string
}

const ITUNES = "https://itunes.apple.com"

export async function itunes(path: string, params: Record<string, string>): Promise<RawResult[]> {
  const qs = new URLSearchParams(params).toString()
  try {
    const res = await fetch(`${ITUNES}${path}?${qs}`, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      },
      cache: "no-store",
    })
    if (!res.ok) return []
    const data = (await res.json()) as { results?: RawResult[] }
    return data.results ?? []
  } catch (err) {
    console.error("iTunes API fetch error:", err)
    return []
  }
}

export function normalize(raw: RawResult[]): Track[] {
  const out: Track[] = []
  for (const r of raw) {
    if (r.kind !== "song") continue
    if (!r.trackId || !r.trackName || !r.artistName || !r.previewUrl) continue
    out.push({
      trackId: r.trackId,
      name: r.trackName,
      artist: r.artistName,
      artistId: r.artistId ?? 0,
      genre: r.primaryGenreName ?? "Unknown",
      artwork: (r.artworkUrl100 ?? "").replace("100x100bb", "300x300bb"),
      previewUrl: r.previewUrl,
      album: r.collectionName ?? "",
      year: r.releaseDate ? r.releaseDate.slice(0, 4) : "",
    })
  }
  return out
}

export function dedupe(tracks: Track[]): Track[] {
  const seen = new Set<string>()
  const out: Track[] = []
  for (const t of tracks) {
    const key = `${t.name.toLowerCase().replace(/\(.*\)|\[.*\]/g, "").trim()}::${t.artist.toLowerCase()}`
    if (seen.has(key)) continue
    seen.add(key)
    out.push(t)
  }
  return out
}

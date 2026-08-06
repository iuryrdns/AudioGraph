import { dedupe, itunes, normalize } from "@/lib/itunes"

const JUNK = /kidz bop|karaoke|tribute|instrumental version|made famous|8-bit|lullaby|cover band/i

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const q = (searchParams.get("q") ?? "").trim()
  const engine = searchParams.get("engine")
  const allowFallback = searchParams.get("allowFallback") === "1"
  if (q.length < 2) return Response.json({ results: [], source: "itunes" })

  if (engine === "python" && !allowFallback) {
    try {
      const pythonBase = process.env.PYTHON_ENGINE_URL || "http://127.0.0.1:8000"
      const pyRes = await fetch(`${pythonBase}/api/py/search?q=${encodeURIComponent(q)}`, {
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      })
      if (pyRes.ok) {
        const pyData = await pyRes.json()
        if (pyData.results && pyData.results.length > 0) {
          return Response.json({ ...pyData, source: "python" })
        }
      }
    } catch {
      // Python engine unreachable.
    }
    // Python engine found nothing (or is offline). Do NOT silently query
    // iTunes here — tell the frontend so it can ask the user first. The
    // frontend re-requests with allowFallback=1 if the user says yes.
    return Response.json({ results: [], source: "python", needsFallback: true })
  }

  const raw = await itunes("/search", {
    term: q,
    entity: "song",
    media: "music",
    limit: "25",
  })

  const results = dedupe(normalize(raw))
    .filter((t) => !JUNK.test(t.artist) && !JUNK.test(t.album))
    .slice(0, 8)

  // `source` tells the UI which engine actually answered this request, so it
  // can warn the user when they asked for "python" but got iTunes text-search
  // results instead (these tracks are NOT in the recommendation graph).
  return Response.json({ results, source: "itunes" })
}

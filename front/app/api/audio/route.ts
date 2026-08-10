import { NextRequest } from "next/server"

const ALLOWED_HOSTS = [
  "cdnt-preview.dzcdn.net",
  "audio-ssl.itunes.apple.com",
  "mzstatic.com",
  "deezer.com",
]

async function searchItunes(term: string, country?: string): Promise<string | null> {
  try {
    const params = new URLSearchParams({ term, entity: "song", limit: "1" })
    if (country) params.set("country", country)
    const res = await fetch(`https://itunes.apple.com/search?${params.toString()}`, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
      },
      cache: "no-store",
    })
    if (res.ok) {
      const data = (await res.json()) as { results?: { previewUrl?: string }[] }
      return data.results?.[0]?.previewUrl || null
    }
  } catch {
    // Ignore error
  }
  return null
}

async function fetchItunesPreview(trackName: string, artistName: string): Promise<string | null> {
  const q = `${trackName} ${artistName}`.trim()

  // Default (US) storefront first.
  const usResult = await searchItunes(q)
  if (usResult) return usResult

  // A lot of this catalog is regional Brazilian music (forró, sertanejo,
  // samba, axé, MPB...) that's often missing from the US storefront but
  // present on the Brazilian one — retry there before giving up.
  const brResult = await searchItunes(q, "BR")
  if (brResult) return brResult

  return null
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const urlParam = searchParams.get("url")
  const trackName = searchParams.get("name") || ""
  const artistName = searchParams.get("artist") || ""

  let targetAudioUrl: string | null = null

  // If urlParam is valid and not an expired dzcdn.net URL, try it directly
  if (urlParam && urlParam.startsWith("http") && !urlParam.includes("dzcdn.net") && !urlParam.includes("deezer.com")) {
    try {
      const parsedUrl = new URL(urlParam)
      const isAllowed = ALLOWED_HOSTS.some(
        (host) => parsedUrl.hostname === host || parsedUrl.hostname.endsWith(`.${host}`)
      )
      if (isAllowed) {
        targetAudioUrl = urlParam
      }
    } catch {
      // Invalid URL format
    }
  }

  // If no valid target URL yet, search iTunes directly using track & artist name
  if (!targetAudioUrl && trackName) {
    targetAudioUrl = await fetchItunesPreview(trackName, artistName)
  }

  // Fallback: if urlParam was provided (even if dzcdn), attempt fetching it as last resort
  if (!targetAudioUrl && urlParam && urlParam.startsWith("http")) {
    targetAudioUrl = urlParam
  }

  if (!targetAudioUrl) {
    return new Response("No playable audio stream available", { status: 404 })
  }

  try {
    const rangeHeader = request.headers.get("range")
    const fetchHeaders: Record<string, string> = {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    if (rangeHeader) {
      fetchHeaders["range"] = rangeHeader
    }

    let audioRes = await fetch(targetAudioUrl, {
      headers: fetchHeaders,
      cache: "no-store",
    })

    // If upstream fetch failed (e.g. 403 Forbidden on expired URL), attempt iTunes search fallback
    if (!audioRes.ok && audioRes.status !== 206 && trackName) {
      const freshItunesUrl = await fetchItunesPreview(trackName, artistName)
      if (freshItunesUrl && freshItunesUrl !== targetAudioUrl) {
        audioRes = await fetch(freshItunesUrl, {
          headers: fetchHeaders,
          cache: "no-store",
        })
      }
    }

    if (!audioRes.ok && audioRes.status !== 206) {
      return new Response(`Failed to fetch upstream audio: ${audioRes.status}`, {
        status: audioRes.status,
      })
    }

    const responseHeaders = new Headers()
    responseHeaders.set("Content-Type", audioRes.headers.get("content-type") || "audio/mpeg")
    responseHeaders.set("Accept-Ranges", "bytes")
    responseHeaders.set("Access-Control-Allow-Origin", "*")
    responseHeaders.set("Cache-Control", "public, max-age=86400")

    const contentLength = audioRes.headers.get("content-length")
    if (contentLength) responseHeaders.set("Content-Length", contentLength)

    const contentRange = audioRes.headers.get("content-range")
    if (contentRange) responseHeaders.set("Content-Range", contentRange)

    return new Response(audioRes.body, {
      status: audioRes.status,
      headers: responseHeaders,
    })
  } catch (err) {
    console.error("Audio proxy error:", err)
    return new Response("Error streaming audio", { status: 502 })
  }
}
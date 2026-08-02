import type { Track } from "@/lib/itunes"

export type Feedback = "like" | "dislike" | null

export type GraphNode = {
  id: string
  track: Track
  parentId: string | null
  depth: number
  feedback: Feedback
  expanded: boolean
  loading: boolean
}

export function buildFeedback(nodes: GraphNode[]) {
  const likedArtists: string[] = []
  const likedGenres: string[] = []
  const dislikedArtists: string[] = []
  const dislikedGenres: string[] = []
  for (const node of nodes) {
    if (node.feedback === "like") {
      likedArtists.push(node.track.artist)
      likedGenres.push(node.track.genre)
    } else if (node.feedback === "dislike") {
      dislikedArtists.push(node.track.artist)
      dislikedGenres.push(node.track.genre)
    }
  }
  // um gênero só é rejeitado se nunca foi curtido
  return {
    likedArtists,
    likedGenres,
    dislikedArtists,
    dislikedGenres: dislikedGenres.filter((g) => !likedGenres.includes(g)),
  }
}

/** Faixas ainda não tocadas e não descartadas, na ordem em que o player vai usá-las. */
export function buildQueue(nodes: GraphNode[], currentId: string | null, played: Set<string>) {
  const seenIds = new Set<string>()
  const available = nodes.filter(
    (node) => {
      if (node.id === currentId || played.has(node.id) || node.feedback === "dislike") return false
      if (seenIds.has(node.id)) return false
      seenIds.add(node.id)
      return true
    },
  )
  const current = currentId ? (nodes.find((node) => node.id === currentId) ?? null) : null
  if (!current) return available

  const priority = (node: GraphNode) => {
    if (node.parentId === current.id) return 0
    const parent = node.parentId ? nodes.find((item) => item.id === node.parentId) : null
    if (parent?.feedback === "like") return 1
    if (node.parentId === current.parentId) return 2
    return 3
  }

  return available
    .map((node, index) => ({ node, index, rank: priority(node) }))
    .sort((a, b) => a.rank - b.rank || Math.abs(a.node.depth - current.depth) - Math.abs(b.node.depth - current.depth) || a.index - b.index)
    .map((item) => item.node)
}

export type { Track }

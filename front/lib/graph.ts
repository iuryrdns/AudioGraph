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
  const likedTrackIds: string[] = []
  const dislikedTrackIds: string[] = []
  for (const node of nodes) {
    if (node.feedback === "like") {
      likedArtists.push(node.track.artist)
      likedGenres.push(node.track.genre)
      likedTrackIds.push(node.track.trackId)
    } else if (node.feedback === "dislike") {
      dislikedArtists.push(node.track.artist)
      dislikedGenres.push(node.track.genre)
      dislikedTrackIds.push(node.track.trackId)
    }
  }
  // Um gênero só é rejeitado (a nível de texto) se nunca foi curtido — um
  // like real não deveria vetar um gênero inteiro. Isso por si só, porém,
  // deixava dislikes "invisíveis" dentro de gêneros amplos como "Axé/Forró"
  // (cobre desde forró acústico até versões bem mais eletrônicas/produzidas).
  // Por isso mandamos também likedTrackIds/dislikedTrackIds: o backend usa
  // as features de áudio das faixas específicas pra diferenciar dentro do
  // mesmo gênero, em vez de depender só do texto da tag.
  return {
    likedArtists,
    likedGenres,
    dislikedArtists,
    dislikedGenres: dislikedGenres.filter((g) => !likedGenres.includes(g)),
    likedTrackIds,
    dislikedTrackIds,
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

/**
 * Acha em que faixa curtida ancorar a próxima busca de recomendações.
 *
 * Sobe a cadeia de pais a partir de `currentId` procurando a curtida mais
 * próxima. Se a cadeia não passar por nenhuma curtida (comum depois de uma
 * sequência de rejeições), cai pra curtida mais recente em qualquer lugar
 * do grafo. Sem isso, `advance()` acabava usando a própria faixa recém-
 * rejeitada como semente pra buscar "mais candidatos" quando a fila
 * esvaziava — mantendo a recomendação presa no mesmo estilo que o usuário
 * acabou de rejeitar, em vez de voltar pro que ele realmente gostou.
 */
export function findLikedAnchor(nodes: GraphNode[], currentId: string | null): string | null {
  if (!currentId) return null

  let cursor = nodes.find((node) => node.id === currentId) ?? null
  while (cursor) {
    if (cursor.feedback === "like") return cursor.id
    cursor = cursor.parentId ? (nodes.find((node) => node.id === cursor!.parentId) ?? null) : null
  }

  const liked = nodes.filter((node) => node.feedback === "like")
  if (liked.length > 0) return liked[liked.length - 1].id

  // Nenhuma curtida ainda registrada -- não tem em que ancorar, mantém o atual.
  return currentId
}
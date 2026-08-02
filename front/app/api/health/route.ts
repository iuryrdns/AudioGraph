import { NextResponse } from "next/server"

export async function GET() {
  try {
    const pythonBase = process.env.PYTHON_ENGINE_URL || "http://127.0.0.1:8000"
    const res = await fetch(`${pythonBase}/health`, {
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    })
    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }
  } catch {
    // Backend offline
  }
  return NextResponse.json({ status: "offline" }, { status: 503 })
}

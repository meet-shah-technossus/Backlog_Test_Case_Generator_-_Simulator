import { useState, useEffect, useCallback } from 'react'

export function useHealth() {
  const [health, setHealth] = useState(null)   // null | { overall, llm, backlog_api, ... }
  const [loading, setLoading] = useState(false)

  const check = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/health')
      const data = await res.json()
      setHealth(data)
    } catch {
      setHealth({ overall: 'error', llm: { status: 'error' } })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    check()
    const id = setInterval(check, 15_000)
    return () => clearInterval(id)
  }, [check])

  return { health, loading, recheck: check }
}

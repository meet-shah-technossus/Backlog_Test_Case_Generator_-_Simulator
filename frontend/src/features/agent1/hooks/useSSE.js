import { useCallback, useRef, useState } from 'react'

export function useSSE() {
  const [streaming, setStreaming] = useState(false)
  const readerRef = useRef(null)

  const abort = useCallback(() => {
    readerRef.current?.cancel?.()
    readerRef.current = null
    setStreaming(false)
  }, [])

  const start = useCallback(async (url, fetchOptions, onEvent, onDone, onError) => {
    abort()
    setStreaming(true)

    try {
      const res = await fetch(url, {
        ...fetchOptions,
        headers: { 'Content-Type': 'application/json', ...(fetchOptions?.headers ?? {}) },
      })

      if (!res.ok) {
        const txt = await res.text()
        onError?.(`Server error ${res.status}: ${txt}`)
        setStreaming(false)
        return
      }

      if (!res.body) {
        onError?.('Streaming response body is not available')
        setStreaming(false)
        return
      }

      const reader = res.body.getReader()
      readerRef.current = reader
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue

          try {
            const event = JSON.parse(trimmed.slice(6))
            onEvent?.(event)
          } catch {
            // Ignore malformed event chunks.
          }
        }
      }

      onDone?.()
    } catch (e) {
      if (e?.name !== 'AbortError') onError?.(e?.message || 'Stream failed')
    } finally {
      readerRef.current = null
      setStreaming(false)
    }
  }, [abort])

  return { start, abort, streaming }
}

import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import {
  Play, Pause, Square, SkipForward, FileText, Code,
  CheckCircle2, XCircle, Loader, Download, RotateCcw,
  Zap, ClipboardList, FlaskConical, ChevronRight
} from 'lucide-react'
import './DemoBoard.css'

// ── Constants ─────────────────────────────────────────────────────────────────

const DEMO_CRITERIA = [
  "Navigate to Amazon.com homepage and verify page loads correctly with all major UI elements visible",
  "Verify global search bar is visible, enabled, and accepts keyboard input",
  "Search for 'wireless mouse' and verify relevant product results are displayed",
  "Verify product cards display title, price, rating, and thumbnail image correctly",
  "Apply price-based sorting (Low to High) and verify results reorder accordingly",
  "Search for a second product category ('usb keyboard') and verify new results are shown",
  "Search for a third product category ('laptop stand') and verify results with image thumbnails",
  "Navigate to cart page and verify the shopping cart loads correctly",
]

const PHASES = [
  { id: 'cases', label: 'Test Cases', icon: ClipboardList },
  { id: 'scripts', label: 'Test Scripts', icon: Code },
  { id: 'execute', label: 'Execution', icon: FlaskConical },
]

// ── SSE reader helper ─────────────────────────────────────────────────────────

function useStreamReader() {
  const readerRef = useRef(null)
  const pausedRef = useRef(false)
  const bufferRef = useRef([])
  const [streaming, setStreaming] = useState(false)
  const [paused, setPaused] = useState(false)

  const stop = useCallback(() => {
    readerRef.current?.cancel?.()
    readerRef.current = null
    pausedRef.current = false
    bufferRef.current = []
    setStreaming(false)
    setPaused(false)
  }, [])

  const pause = useCallback(() => {
    pausedRef.current = true
    setPaused(true)
  }, [])

  const resume = useCallback((onFlush) => {
    pausedRef.current = false
    setPaused(false)
    if (bufferRef.current.length > 0) {
      const buffered = bufferRef.current.join('')
      bufferRef.current = []
      onFlush?.(buffered)
    }
  }, [])

  const start = useCallback(async (url, onToken, onDone, onError) => {
    stop()
    setStreaming(true)

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) {
        onError?.(`Server error ${res.status}`)
        setStreaming(false)
        return
      }
      if (!res.body) {
        onError?.('No response body')
        setStreaming(false)
        return
      }

      const reader = res.body.getReader()
      readerRef.current = reader
      const decoder = new TextDecoder()
      let buf = ''
      let gotDone = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(trimmed.slice(6))
            if (evt.type === 'token') {
              if (pausedRef.current) {
                bufferRef.current.push(evt.token)
              } else {
                onToken?.(evt.token)
              }
            } else if (evt.type === 'done') {
              gotDone = true
              onDone?.(evt)
            } else if (evt.type === 'error') {
              onError?.(evt.error || 'Stream error')
            }
          } catch { /* skip malformed */ }
        }
      }
      if (!gotDone) onDone?.({ type: 'done' })
    } catch (e) {
      if (e?.name !== 'AbortError') onError?.(e?.message)
    } finally {
      readerRef.current = null
      setStreaming(false)
      setPaused(false)
      pausedRef.current = false
      bufferRef.current = []
    }
  }, [stop])

  return { start, stop, pause, resume, streaming, paused }
}

// ── Main component ────────────────────────────────────────────────────────────

export default function DemoBoard() {
  const [phase, setPhase] = useState('cases') // cases | scripts | execute
  const [casesText, setCasesText] = useState('')
  const [casesComplete, setCasesComplete] = useState(false)
  const [scriptText, setScriptText] = useState('')
  const [scriptComplete, setScriptComplete] = useState(false)
  const [results, setResults] = useState([])
  const [executing, setExecuting] = useState(false)
  const [executionDone, setExecutionDone] = useState(false)
  const [summary, setSummary] = useState(null)
  const [statusMsg, setStatusMsg] = useState('')
  const [screenshotModal, setScreenshotModal] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const streamBoxRef = useRef(null)

  const caseStream = useStreamReader()
  const scriptStream = useStreamReader()

  // Auto-scroll stream box
  const scrollToBottom = useCallback(() => {
    if (streamBoxRef.current) {
      streamBoxRef.current.scrollTop = streamBoxRef.current.scrollHeight
    }
  }, [])

  // ── Generate test cases ───────────────────────────────────────────────────
  const handleGenerateCases = useCallback(() => {
    setCasesText('')
    setCasesComplete(false)
    setErrorMsg('')
    caseStream.start(
      '/demo/generate-test-cases/stream',
      (token) => {
        setCasesText(prev => prev + token)
        setTimeout(scrollToBottom, 10)
      },
      () => setCasesComplete(true),
      (err) => { setErrorMsg(`Test case generation error: ${err}`); console.error(err) }
    )
  }, [caseStream, scrollToBottom])

  const handleCasesResume = useCallback(() => {
    caseStream.resume((buffered) => {
      setCasesText(prev => prev + buffered)
      setTimeout(scrollToBottom, 10)
    })
  }, [caseStream, scrollToBottom])

  // ── Generate test scripts ─────────────────────────────────────────────────
  const handleGenerateScripts = useCallback(() => {
    setScriptText('')
    setScriptComplete(false)
    setErrorMsg('')
    scriptStream.start(
      '/demo/generate-test-scripts/stream',
      (token) => {
        setScriptText(prev => prev + token)
        setTimeout(scrollToBottom, 10)
      },
      () => setScriptComplete(true),
      (err) => { setErrorMsg(`Script generation error: ${err}`); console.error(err) }
    )
  }, [scriptStream, scrollToBottom])

  const handleScriptResume = useCallback(() => {
    scriptStream.resume((buffered) => {
      setScriptText(prev => prev + buffered)
      setTimeout(scrollToBottom, 10)
    })
  }, [scriptStream, scrollToBottom])

  // ── Load demo script ──────────────────────────────────────────────────────
  const handleLoadDemoScript = useCallback(async () => {
    scriptStream.stop()
    try {
      const res = await fetch('/demo/script')
      const data = await res.json()
      setScriptText(data.script || '')
      setScriptComplete(true)
    } catch (e) {
      console.error('Failed to load demo script:', e)
    }
  }, [scriptStream])

  // ── Execute tests ─────────────────────────────────────────────────────────
  const executionReaderRef = useRef(null)

  const handleExecute = useCallback(async () => {
    setResults([])
    setSummary(null)
    setStatusMsg('')
    setExecuting(true)
    setExecutionDone(false)

    try {
      const res = await fetch('/demo/execute/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok || !res.body) {
        setStatusMsg('Failed to start execution')
        setExecuting(false)
        return
      }

      const reader = res.body.getReader()
      executionReaderRef.current = reader
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(trimmed.slice(6))
            if (evt.type === 'status') {
              setStatusMsg(evt.message)
            } else if (evt.type === 'test-start') {
              setResults(prev => [
                ...prev,
                { testId: evt.testId, name: evt.name, status: 'running' },
              ])
            } else if (evt.type === 'test-result') {
              setResults(prev =>
                prev.map(r =>
                  r.testId === evt.testId
                    ? { ...r, status: evt.status, error: evt.error, screenshot: evt.screenshot }
                    : r
                )
              )
            } else if (evt.type === 'summary') {
              setSummary(evt)
            } else if (evt.type === 'stream-end') {
              // done
            }
          } catch { /* skip */ }
        }
      }
    } catch (e) {
      setStatusMsg(`Execution failed: ${e?.message}`)
    } finally {
      executionReaderRef.current = null
      setExecuting(false)
      setExecutionDone(true)
    }
  }, [])

  const handleStopExecution = useCallback(() => {
    executionReaderRef.current?.cancel?.()
    executionReaderRef.current = null
    setExecuting(false)
    setExecutionDone(true)
    setStatusMsg('Execution stopped by user.')
  }, [])

  // ── Reset all ─────────────────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    caseStream.stop()
    scriptStream.stop()
    handleStopExecution()
    setCasesText('')
    setCasesComplete(false)
    setScriptText('')
    setScriptComplete(false)
    setResults([])
    setSummary(null)
    setStatusMsg('')
    setErrorMsg('')
    setExecutionDone(false)
    setPhase('cases')
  }, [caseStream, scriptStream, handleStopExecution])

  // ── Save & Continue ───────────────────────────────────────────────────────
  const handleSaveAndContinue = useCallback(() => {
    if (phase === 'cases') {
      caseStream.stop()
      setCasesComplete(true)
      setPhase('scripts')
    } else if (phase === 'scripts') {
      scriptStream.stop()
      setScriptComplete(true)
      setPhase('execute')
    }
  }, [phase, caseStream, scriptStream])

  // ── Computed ──────────────────────────────────────────────────────────────
  const passedCount = useMemo(
    () => results.filter(r => r.status === 'passed').length,
    [results]
  )
  const failedCount = useMemo(
    () => results.filter(r => r.status === 'failed').length,
    [results]
  )

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="demo-wrap">
      {/* Header */}
      <div className="demo-head">
        <div>
          <h3>Demo — Amazon Shopping Flow</h3>
          <p>End-to-end test generation and execution demo for Amazon.com</p>
        </div>
        <button className="demo-btn" onClick={handleReset}>
          <RotateCcw size={12} /> Reset
        </button>
      </div>

      {/* Phase tabs */}
      <div className="demo-phases">
        {PHASES.map((p, i) => {
          const Icon = p.icon
          const active = phase === p.id
          const done =
            (p.id === 'cases' && casesComplete) ||
            (p.id === 'scripts' && scriptComplete) ||
            (p.id === 'execute' && executionDone)
          return (
            <button
              key={p.id}
              className={`demo-phase-btn ${active ? 'demo-phase-btn-active' : ''} ${done && !active ? 'demo-phase-btn-done' : ''}`}
              onClick={() => setPhase(p.id)}
            >
              {done && !active ? <CheckCircle2 size={12} /> : <Icon size={12} />}
              <span>{i + 1}. {p.label}</span>
            </button>
          )
        })}
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div style={{ padding: '0.5rem 0.75rem', borderRadius: '0.375rem', background: 'color-mix(in srgb, #ef4444 14%, transparent)', border: '1px solid color-mix(in srgb, #ef4444 30%, transparent)', color: '#ef4444', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
          <XCircle size={13} /> {errorMsg}
        </div>
      )}

      {/* ── Phase 1: Test Cases ──────────────────────────────────────────── */}
      {phase === 'cases' && (
        <>
          {/* Acceptance criteria card */}
          <div className="demo-card">
            <div className="demo-card-head">
              <FileText size={12} /> Acceptance Criteria (Sample Data)
            </div>
            <div className="demo-criteria-list">
              {DEMO_CRITERIA.map((c, i) => (
                <div key={i} className="demo-criteria-item">
                  <span className="demo-criteria-num">{i + 1}</span>
                  <span>{c}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Controls */}
          <div className="demo-controls">
            {!caseStream.streaming && !casesComplete && (
              <button className="demo-btn demo-btn-primary" onClick={handleGenerateCases}>
                <Zap size={12} /> Generate Test Cases
              </button>
            )}
            {caseStream.streaming && !caseStream.paused && (
              <button className="demo-btn demo-btn-warn" onClick={caseStream.pause}>
                <Pause size={12} /> Pause
              </button>
            )}
            {caseStream.streaming && caseStream.paused && (
              <button className="demo-btn demo-btn-primary" onClick={handleCasesResume}>
                <Play size={12} /> Resume
              </button>
            )}
            {caseStream.streaming && (
              <button className="demo-btn demo-btn-danger" onClick={() => { caseStream.stop(); setCasesComplete(true) }}>
                <Square size={12} /> Stop
              </button>
            )}
            {(casesText.length > 0) && (
              <button className="demo-btn demo-btn-success" onClick={handleSaveAndContinue}>
                <SkipForward size={12} /> Save & Continue
              </button>
            )}
          </div>

          {/* Streaming output */}
          {casesText && (
            <div className="demo-stream-box" ref={streamBoxRef}>
              {casesText}
              {caseStream.streaming && <span className="demo-stream-cursor" />}
            </div>
          )}
        </>
      )}

      {/* ── Phase 2: Test Scripts ────────────────────────────────────────── */}
      {phase === 'scripts' && (
        <>
          {/* Controls */}
          <div className="demo-controls">
            {!scriptStream.streaming && !scriptComplete && (
              <button className="demo-btn demo-btn-primary" onClick={handleGenerateScripts}>
                <Code size={12} /> Generate Test Scripts
              </button>
            )}
            {scriptStream.streaming && !scriptStream.paused && (
              <button className="demo-btn demo-btn-warn" onClick={scriptStream.pause}>
                <Pause size={12} /> Pause
              </button>
            )}
            {scriptStream.streaming && scriptStream.paused && (
              <button className="demo-btn demo-btn-primary" onClick={handleScriptResume}>
                <Play size={12} /> Resume
              </button>
            )}
            {scriptStream.streaming && (
              <button className="demo-btn demo-btn-danger" onClick={() => { scriptStream.stop(); setScriptComplete(true) }}>
                <Square size={12} /> Stop
              </button>
            )}
            <button className="demo-btn demo-btn-success" onClick={handleLoadDemoScript}>
              <Download size={12} /> Load Demo Script
            </button>
            {scriptComplete && (
              <button className="demo-btn demo-btn-primary" onClick={handleSaveAndContinue}>
                <SkipForward size={12} /> Save & Continue
              </button>
            )}
          </div>

          {/* Streaming output */}
          <div className="demo-stream-box" ref={streamBoxRef}>
            {scriptText || (
              <span style={{ color: 'var(--app-muted)' }}>
                Click "Generate Test Scripts" or "Load Demo Script" to begin...
              </span>
            )}
            {scriptStream.streaming && <span className="demo-stream-cursor" />}
          </div>
        </>
      )}

      {/* ── Phase 3: Execution ───────────────────────────────────────────── */}
      {phase === 'execute' && (
        <>
          {/* Controls */}
          <div className="demo-controls">
            {!executing && !executionDone && (
              <button className="demo-btn demo-btn-primary" onClick={handleExecute}>
                <Play size={12} /> Execute Tests in Browser
              </button>
            )}
            {executing && (
              <button className="demo-btn demo-btn-danger" onClick={handleStopExecution}>
                <Square size={12} /> Stop Execution
              </button>
            )}
            {executionDone && (
              <button className="demo-btn demo-btn-primary" onClick={handleExecute}>
                <RotateCcw size={12} /> Re-run Tests
              </button>
            )}
            {executing && (
              <span style={{ fontSize: 11, color: 'var(--app-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <span className="demo-spinner" /> {statusMsg || 'Executing...'}
              </span>
            )}
          </div>

          {/* Results table */}
          {results.length > 0 && (
            <div className="demo-card">
              <div className="demo-card-head">
                <FlaskConical size={12} /> Test Execution Results
              </div>
              <table className="demo-results-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Test Case</th>
                    <th>Status</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map(r => (
                    <tr key={r.testId}>
                      <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{r.testId}</td>
                      <td>{r.name}</td>
                      <td>
                        {r.status === 'running' && (
                          <span className="demo-result-running" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Loader size={12} className="animate-spin" /> Running
                          </span>
                        )}
                        {r.status === 'passed' && (
                          <span className="demo-result-passed" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CheckCircle2 size={12} /> Passed
                          </span>
                        )}
                        {r.status === 'failed' && (
                          <span className="demo-result-failed" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <XCircle size={12} /> Failed
                          </span>
                        )}
                      </td>
                      <td>
                        {r.error && (
                          <div style={{ fontSize: 11, color: '#ef4444', maxWidth: 360 }}>
                            {r.error.length > 120 ? r.error.slice(0, 120) + '…' : r.error}
                          </div>
                        )}
                        {r.screenshot && (
                          <img
                            src={`data:image/png;base64,${r.screenshot}`}
                            alt={`Failure screenshot — ${r.testId}`}
                            className="demo-screenshot-thumb"
                            onClick={() => setScreenshotModal(r.screenshot)}
                          />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Summary */}
          {summary && (
            <div className="demo-summary">
              <div className="demo-summary-stat">
                <span className="demo-summary-val" style={{ color: 'var(--app-text)' }}>{summary.total}</span>
                <span className="demo-summary-label">Total</span>
              </div>
              <div className="demo-summary-stat">
                <span className="demo-summary-val demo-result-passed">{summary.passed}</span>
                <span className="demo-summary-label">Passed</span>
              </div>
              <div className="demo-summary-stat">
                <span className="demo-summary-val demo-result-failed">{summary.failed}</span>
                <span className="demo-summary-label">Failed</span>
              </div>
              <div style={{ flex: 1, textAlign: 'right', fontSize: 11, color: 'var(--app-muted)' }}>
                {statusMsg}
              </div>
            </div>
          )}
        </>
      )}

      {/* Screenshot modal */}
      {screenshotModal && (
        <div className="demo-modal-overlay" onClick={() => setScreenshotModal(null)}>
          <img
            src={`data:image/png;base64,${screenshotModal}`}
            alt="Failure screenshot — full size"
            className="demo-modal-img"
            onClick={e => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

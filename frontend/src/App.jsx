import { useState, useMemo, useCallback, useEffect } from 'react'
import { Sparkles, ArrowRight, BookOpen, Zap, Bot, ChevronLeft, ChevronRight, LineChart, Monitor } from 'lucide-react'
import './App.css'

import { useHealth }    from './hooks/useHealth.js'
import { useBacklog }   from './hooks/useBacklog.js'

import { ToastProvider }  from './contexts/ToastContext.jsx'
import { ThemeProvider } from './contexts/ThemeContext.jsx'
import ErrorBoundary      from './components/ErrorBoundary.jsx'
import Header             from './components/Header.jsx'
import Sidebar            from './components/Sidebar.jsx'
import Agent1RunBoard     from './features/agent1/components/Agent1RunBoard.jsx'
import Agent2Board        from './features/agent2/components/Agent2Board.jsx'
import Agent3Board        from './features/agent3/components/Agent3Board.jsx'
import Agent4Board        from './features/agent4/components/Agent4Board.jsx'
import Agent5Board        from './features/agent5/components/Agent5Board.jsx'
import EvaluationBoard    from './features/evaluation/components/EvaluationBoard.jsx'
import QueueOpsPanel      from './components/QueueOpsPanel.jsx'
import DemoBoard          from './features/demo/components/DemoBoard.jsx'

const PAGES = [
  { id: 'agent1', path: '/agent1', label: 'Agent 1', icon: Sparkles },
  { id: 'agent2', path: '/agent2', label: 'Agent 2', icon: ArrowRight },
  { id: 'agent3', path: '/agent3', label: 'Agent 3', icon: Bot },
  { id: 'agent4', path: '/agent4', label: 'Agent 4', icon: Bot },
  { id: 'agent5', path: '/agent5', label: 'Agent 5', icon: Bot },
  { id: 'evaluation', path: '/evaluation', label: 'Evaluation', icon: LineChart },
  { id: 'queue-ops', path: '/queue-ops', label: 'Queue Ops', icon: LineChart },
  { id: 'demo', path: '/demo', label: 'Demo', icon: Monitor },
]

function pathToPage(path) {
  if (path === '/agent2') return 'agent2'
  if (path === '/agent3') return 'agent3'
  if (path === '/agent4') return 'agent4'
  if (path === '/agent5') return 'agent5'
  if (path === '/evaluation') return 'evaluation'
  if (path === '/queue-ops') return 'queue-ops'
  if (path === '/demo') return 'demo'
  return 'agent1'
}

// ── Workflow step cards shown when no story is selected ────────────────────
const STEPS = [
  { n: 1, icon: BookOpen, color: 'text-blue-400',   label: 'Load Backlog',      detail: 'Use the sidebar to load sample or live API data' },
  { n: 2, icon: Zap,      color: 'text-violet-400', label: 'Pick a Story',      detail: 'Select any user story from the Epic → Feature tree' },
  { n: 3, icon: Sparkles, color: 'text-teal-400',   label: 'Generate Tests',    detail: 'AI generates structured test cases per acceptance criterion' },
  { n: 4, icon: ArrowRight, color: 'text-cyan-400', label: 'Handoff to Agent 2', detail: 'Approved artifacts move to the next agent contract' },
]

function WelcomeScreen() {
  return (
    <div className="welcome-wrap animate-fade-in">
      <div className="welcome-card">
        {/* Hero */}
        <div className="welcome-hero">
          <div className="welcome-icon bg-gradient-brand shadow-lg shadow-violet-500/20">
            <Zap size={24} className="text-white" />
          </div>
          <h2 className="text-xl font-semibold gradient-text mb-2">
            AI Test Automation
          </h2>
          <p className="welcome-subtitle">
            Backlog {'->'} Agent 1 {'->'} Human Review {'->'} Agent 2 handoff.
          </p>
        </div>

        {/* Steps */}
        <div className="welcome-steps">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <div key={step.n} className="glass welcome-step-card">
                <div className={`w-7 h-7 rounded-full border border-current/20 bg-current/10 flex items-center justify-center flex-shrink-0 ${step.color}`}>
                  <Icon size={13} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="welcome-step-index">0{step.n}</span>
                    <span className="welcome-step-label">{step.label}</span>
                  </div>
                  <p className="welcome-step-detail">{step.detail}</p>
                </div>
                {i < STEPS.length - 1 && (
                  <ArrowRight size={11} className="welcome-step-arrow" />
                )}
              </div>
            )
          })}
        </div>

        <p className="welcome-hint">
          Start by clicking <span className="welcome-hint-emphasis">Load Sample Backlog</span> in the sidebar →
        </p>
      </div>
    </div>
  )
}

// ── Inner app (needs to be inside ToastProvider) ───────────────────────────
function AppInner() {
  const { health, recheck }  = useHealth()
  const {
    backlog, loading: backlogLoading, error: backlogError, source,
    loadFromAPI, loadSample, refreshBacklog,
  } = useBacklog()
  const [selectedId, setSelectedId] = useState(null)
  const [activePage, setActivePage] = useState(() => {
    return pathToPage(window.location.pathname)
  })

  const switchPage = useCallback((nextPage) => {
    const page = PAGES.find((p) => p.id === nextPage) || PAGES[0]
    window.history.pushState({}, '', page.path)
    setActivePage(page.id)
  }, [])

  useEffect(() => {
    const onPop = () => {
      setActivePage(pathToPage(window.location.pathname))
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const selectStory = useCallback((id) => {
    setSelectedId(id)
    if (id && activePage !== 'agent1') {
      switchPage('agent1')
    }
  }, [activePage, switchPage])

  const { selectedStory, selectedFeature, selectedEpic } = useMemo(() => {
    if (!backlog || !selectedId) return {}
    for (const epic of backlog.epics ?? []) {
      for (const feature of epic.features ?? []) {
        for (const story of feature.user_stories ?? []) {
          if (story.id === selectedId)
            return { selectedStory: story, selectedFeature: feature, selectedEpic: epic }
        }
      }
    }
    return {}
  }, [backlog, selectedId])

  const quickQueue = useMemo(() => {
    if (!selectedStory) {
      return [{ id: 'pick-story', label: 'Select a story in backlog', action: () => {}, disabled: true, pageId: null }]
    }
    return [
      { id: 'go-agent1', label: 'Generate or review in Agent 1', action: () => switchPage('agent1'), disabled: false, pageId: 'agent1' },
      { id: 'go-agent2', label: 'Confirm step handoff in Agent 2', action: () => switchPage('agent2'), disabled: false, pageId: 'agent2' },
      { id: 'go-agent3', label: 'Inspect selectors in Agent 3', action: () => switchPage('agent3'), disabled: false, pageId: 'agent3' },
      { id: 'go-agent4', label: 'Review script and execution in Agent 4', action: () => switchPage('agent4'), disabled: false, pageId: 'agent4' },
      { id: 'go-agent5', label: 'Verify analysis and reliability in Agent 5', action: () => switchPage('agent5'), disabled: false, pageId: 'agent5' },
      { id: 'go-evaluation', label: 'Inspect rollout metrics in Evaluation', action: () => switchPage('evaluation'), disabled: false, pageId: 'evaluation' },
      { id: 'go-queue-ops', label: 'Operate queue controls in Queue Ops', action: () => switchPage('queue-ops'), disabled: false, pageId: 'queue-ops' },
    ]
  }, [selectedStory, switchPage])

  const flowIndex = useMemo(() => PAGES.findIndex((page) => page.id === activePage), [activePage])
  const prevPageId = flowIndex > 0 ? PAGES[flowIndex - 1].id : null
  const nextPageId = flowIndex >= 0 && flowIndex < PAGES.length - 1 ? PAGES[flowIndex + 1].id : null

  return (
    <div className="app-shell">
      <Header health={health} onRecheck={recheck} />

      <div className="app-body">
        <Sidebar
          backlog={backlog}
          loading={backlogLoading}
          error={backlogError}
          source={source}
          selectedId={selectedId}
          onSelect={selectStory}
          onLoadSample={loadSample}
          onLoadAPI={loadFromAPI}
          onRefresh={refreshBacklog}
        />

        <main className="app-main">
          {/* When no story is selected, show the welcome screen */}
          {!selectedStory ? (
            <WelcomeScreen />
          ) : (
            <>
              {/* Story context breadcrumb */}
              <div className="story-breadcrumb">
                <span className="story-breadcrumb-node">{selectedEpic?.title}</span>
                <span className="story-breadcrumb-separator">›</span>
                <span className="story-breadcrumb-node">{selectedFeature?.title}</span>
                <span className="story-breadcrumb-separator">›</span>
                <span className="story-breadcrumb-focus">{selectedStory.title}</span>
                <span className="story-chip">
                  {selectedStory.acceptance_criteria?.length ?? 0} criteria
                </span>
              </div>

              {/* Tab bar */}
              <div className="app-tabbar">
                {PAGES.map(page => {
                  const Icon = page.icon
                  const active = activePage === page.id
                  return (
                    <button
                      key={page.id}
                      onClick={() => switchPage(page.id)}
                      className={`app-tab ${active ? 'app-tab-active' : 'app-tab-inactive'}`}
                    >
                      <Icon size={12} />
                      {page.label}
                    </button>
                  )
                })}
              </div>

              <div className="app-action-queue">
                <div className="app-action-queue-head">
                  <div className="app-action-queue-title">Action Queue</div>
                  <div className="app-action-nav">
                    <button
                      className="app-action-nav-btn"
                      onClick={() => prevPageId && switchPage(prevPageId)}
                      disabled={!selectedStory || !prevPageId}
                    >
                      <ChevronLeft size={12} />
                      Previous
                    </button>
                    <button
                      className="app-action-nav-btn app-action-nav-btn-primary"
                      onClick={() => nextPageId && switchPage(nextPageId)}
                      disabled={!selectedStory || !nextPageId}
                    >
                      Next Step
                      <ChevronRight size={12} />
                    </button>
                  </div>
                </div>
                <div className="app-action-queue-items">
                  {quickQueue.map((item) => (
                    <button
                      key={item.id}
                      className={`app-action-chip ${item.pageId === activePage ? 'app-action-chip-current' : ''}`}
                      onClick={item.action}
                      disabled={item.disabled}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Panel */}
              <div className="app-panel-wrap animate-fade-in">
                {activePage === 'agent1' ? (
                  <div className="app-panel">
                    <Agent1RunBoard
                      story={selectedStory}
                      onSuiteReady={() => {}}
                    />
                  </div>
                ) : activePage === 'agent2' ? (
                  <div className="app-panel">
                    <Agent2Board story={selectedStory} />
                  </div>
                ) : activePage === 'agent3' ? (
                  <div className="app-panel">
                    <Agent3Board story={selectedStory} />
                  </div>
                ) : activePage === 'agent4' ? (
                  <div className="app-panel">
                    <Agent4Board story={selectedStory} />
                  </div>
                ) : activePage === 'agent5' ? (
                  <div className="app-panel">
                    <Agent5Board story={selectedStory} />
                  </div>
                ) : activePage === 'queue-ops' ? (
                  <div className="app-panel">
                    <QueueOpsPanel />
                  </div>
                ) : activePage === 'demo' ? (
                  <div className="app-panel">
                    <DemoBoard />
                  </div>
                ) : (
                  <div className="app-panel">
                    <EvaluationBoard story={selectedStory} />
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}

// ── Root export — providers wrap everything ────────────────────────────────
export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <ToastProvider>
          <AppInner />
        </ToastProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}



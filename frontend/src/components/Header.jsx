import { Activity, Moon, Sun, Zap } from 'lucide-react'

import { useTheme } from '../contexts/ThemeContext.jsx'

function StatusDot({ status }) {
  const color =
    status === 'ok'    ? 'bg-teal-400 shadow-teal-400/60' :
    status === 'error' ? 'bg-red-400  shadow-red-400/60'  :
                         'bg-yellow-400 shadow-yellow-400/60'
  return <span className={`inline-block w-2 h-2 rounded-full shadow-sm ${color}`} />
}

export default function Header({ health, onRecheck }) {
  const { theme, toggleTheme } = useTheme()
  const llm  = health?.llm?.status
  const overall = health?.overall

  return (
    <header className="app-header h-14 flex items-center justify-between px-5 backdrop-blur-sm flex-shrink-0 z-10">
      {/* Brand */}
      <div className="flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center">
          <Zap size={14} className="text-white" />
        </div>
        <span className="text-sm font-semibold tracking-tight gradient-text">
          AI Test Automation
        </span>
        <span className="text-white/20 text-xs hidden sm:block">
          · Backlog → LLM → Playwright
        </span>
      </div>

      {/* Status */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleTheme}
          className="app-theme-toggle"
          title={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        >
          {theme === 'dark' ? <Sun size={13} /> : <Moon size={13} />}
          <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
        </button>
        {health && (
          <div className="flex items-center gap-3 text-xs text-white/50">
            <span className="flex items-center gap-1.5">
              <StatusDot status={llm} />
              LLM (OpenAI)
            </span>
            {health.configured_model && (
              <span className="hidden md:inline text-white/30 font-mono text-[11px]">
                {health.configured_model}
              </span>
            )}
          </div>
        )}
        <button
          onClick={onRecheck}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
          title="Refresh health status"
        >
          <Activity size={13} />
          {overall === 'ok' ? (
            <span className="text-teal-400">Healthy</span>
          ) : overall === 'error' ? (
            <span className="text-red-400">Offline</span>
          ) : (
            <span className="text-yellow-400">Degraded</span>
          )}
        </button>
      </div>
    </header>
  )
}

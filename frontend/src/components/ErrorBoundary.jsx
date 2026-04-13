import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

/**
 * React error boundary — catches render/lifecycle errors in the component tree
 * and shows a friendly recovery UI instead of a blank screen.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info?.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="glass p-8 text-center max-w-sm w-full">
            <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle size={22} className="text-red-400" />
            </div>
            <h3 className="text-sm font-semibold text-white/80 mb-2">Something went wrong</h3>
            <p className="text-[11px] text-white/40 mb-5 font-mono break-all leading-relaxed bg-white/[0.02] rounded-lg p-3 border border-white/8">
              {this.state.error.message}
            </p>
            <button
              onClick={this.reset}
              className="flex items-center gap-2 mx-auto px-4 py-2 text-xs rounded-lg
                         bg-white/5 border border-white/10 text-white/60
                         hover:text-white/90 hover:bg-white/10 transition-all"
            >
              <RefreshCw size={12} />
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

import { useState } from 'react'
import {
  FolderOpen, BookOpen, FileText, ChevronDown, ChevronRight,
  RefreshCw, Database, Layers
} from 'lucide-react'
import './sidebar.css'

function EpicNode({ epic, selectedId, onSelect }) {
  const [open, setOpen] = useState(true)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="sidebar-node-btn"
      >
        {open
          ? <ChevronDown size={12} className="sidebar-node-chevron" />
          : <ChevronRight size={12} className="sidebar-node-chevron" />}
        <Layers size={13} className="sidebar-epic-icon" />
        <span className="sidebar-epic-title">{epic.title}</span>
      </button>

      {open && (
        <div className="sidebar-node-children">
          {epic.features?.map(feature => (
            <FeatureNode
              key={feature.id}
              feature={feature}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FeatureNode({ feature, selectedId, onSelect }) {
  const [open, setOpen] = useState(true)
  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className="sidebar-node-btn"
      >
        {open
          ? <ChevronDown size={11} className="sidebar-node-chevron" />
          : <ChevronRight size={11} className="sidebar-node-chevron" />}
        <FolderOpen size={12} className="sidebar-feature-icon" />
        <span className="sidebar-feature-title">{feature.title}</span>
      </button>

      {open && (
        <div className="sidebar-node-children">
          {feature.user_stories?.map(story => (
            <StoryNode
              key={story.id}
              story={story}
              selected={story.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StoryNode({ story, selected, onSelect }) {
  const acCount = story.acceptance_criteria?.length ?? 0
  return (
    <button
      onClick={() => onSelect(story.id)}
      className={selected ? 'sidebar-story-btn sidebar-story-btn-active' : 'sidebar-story-btn'}
    >
      <FileText size={12} className={selected ? 'sidebar-story-icon sidebar-story-icon-active' : 'sidebar-story-icon'} />
      <div className="sidebar-story-copy">
        <div className="sidebar-story-title">{story.title}</div>
        <div className="sidebar-story-meta">{acCount} criteria</div>
      </div>
    </button>
  )
}

export default function Sidebar({
  backlog, loading, error, source,
  selectedId, onSelect,
  onLoadSample, onLoadAPI, onRefresh
}) {
  const totalStories  = backlog?.total_stories ?? 0
  const totalCriteria = backlog?.total_criteria ?? 0

  return (
    <aside className="sidebar-root">
      {/* Sidebar header */}
      <div className="sidebar-header flex-shrink-0">
        <div className="sidebar-title-row">
          <span className="sidebar-title">Backlog</span>
          {backlog && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="sidebar-refresh-btn"
              title="Refresh backlog"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            </button>
          )}
        </div>

        {backlog ? (
          <div className="sidebar-stats">
            <span>{backlog.epics?.length ?? 0} epics</span>
            <span>·</span>
            <span>{totalStories} stories</span>
            <span>·</span>
            <span>{totalCriteria} criteria</span>
          </div>
        ) : (
          <p className="sidebar-empty">No backlog loaded</p>
        )}
      </div>

      {/* Load buttons (only when no backlog) */}
      {!backlog && !loading && (
        <div className="sidebar-actions flex-shrink-0">
          <button
            onClick={onLoadSample}
            className="sidebar-btn"
          >
            <BookOpen size={13} />
            Load Sample Backlog
          </button>
          <button
            onClick={onLoadAPI}
            className="sidebar-btn sidebar-btn-primary"
          >
            <Database size={13} />
            Load from API
          </button>
        </div>
      )}

      {/* Loading — shimmer skeleton tree */}
      {loading && (
        <div className="flex-1 overflow-hidden py-2 px-2 space-y-1">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-2">
              <div className="w-2.5 h-2.5 skeleton rounded-full flex-shrink-0" />
              <div
                className="h-2.5 skeleton"
                style={{ width: `${48 + (i % 3) * 16}%` }}
              />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="sidebar-error">
          {error}
        </div>
      )}

      {/* Tree */}
      {backlog && (
        <div className="sidebar-tree">
          {backlog.epics?.map(epic => (
            <EpicNode
              key={epic.id}
              epic={epic}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}

      {/* Source badge */}
      {source && (
        <div className="sidebar-source flex-shrink-0">
          <span className={`sidebar-source-pill ${
            source === 'sample'
              ? 'text-yellow-400/70 border-yellow-400/20 bg-yellow-400/5'
              : 'text-teal-400/70 border-teal-400/20 bg-teal-400/5'
          }`}>
            {source === 'sample' ? '⬡ sample data' : '⬡ live API'}
          </span>
        </div>
      )}
    </aside>
  )
}

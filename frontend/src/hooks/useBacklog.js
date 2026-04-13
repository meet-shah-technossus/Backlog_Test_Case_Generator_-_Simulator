import { useState, useCallback } from 'react'

function mapIntakeItemsToBacklog(items) {
  const epicMap = new Map()

  for (const item of items || []) {
    const epicId = item.epic_id || 'epic_unknown'
    const featureId = item.feature_id || 'feature_unknown'

    if (!epicMap.has(epicId)) {
      epicMap.set(epicId, {
        id: epicId,
        title: item.epic_title || 'Untitled Epic',
        description: '',
        features: [],
        _featureMap: new Map(),
      })
    }

    const epic = epicMap.get(epicId)
    if (!epic._featureMap.has(featureId)) {
      const feature = {
        id: featureId,
        title: item.feature_title || 'Untitled Feature',
        description: '',
        user_stories: [],
      }
      epic._featureMap.set(featureId, feature)
      epic.features.push(feature)
    }

    const feature = epic._featureMap.get(featureId)
    feature.user_stories.push({
      id: item.backlog_item_id,
      title: item.title,
      description: item.description || '',
      target_url: item.target_url || '',
      acceptance_criteria: (item.acceptance_criteria || []).map((text, idx) => ({
        id: `${item.backlog_item_id}_ac_${idx + 1}`,
        text,
      })),
    })
  }

  const epics = Array.from(epicMap.values()).map((epic) => {
    delete epic._featureMap
    return epic
  })

  const totalStories = epics.reduce((acc, epic) => acc + (epic.features || []).reduce((s, f) => s + (f.user_stories || []).length, 0), 0)
  const totalCriteria = epics.reduce(
    (acc, epic) => acc + (epic.features || []).reduce(
      (facc, feature) => facc + (feature.user_stories || []).reduce((sacc, story) => sacc + (story.acceptance_criteria || []).length, 0),
      0,
    ),
    0,
  )

  return {
    epics,
    total_stories: totalStories,
    total_criteria: totalCriteria,
  }
}

export function useBacklog() {
  const [backlog, setBacklog] = useState(null)   // BacklogData | null
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [source, setSource]   = useState(null)   // 'api' | 'sample'

  const _loadFromIntake = useCallback(async (sourceType, srcLabel) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/agent1/intake/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_type: sourceType }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
      const data = await res.json()
      const mapped = mapIntakeItemsToBacklog(data.items || [])
      setBacklog(mapped)
      setSource(srcLabel)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFromAPI   = useCallback(() => _loadFromIntake('api', 'api'), [_loadFromIntake])
  const loadSample    = useCallback(() => _loadFromIntake('sample_db', 'sample'), [_loadFromIntake])
  const refreshBacklog = useCallback(async () => {
    if (source === 'sample') {
      await _loadFromIntake('sample_db', 'sample')
      return
    }
    await _loadFromIntake('api', 'api')
  }, [_loadFromIntake, source])

  return { backlog, loading, error, source, loadFromAPI, loadSample, refreshBacklog }
}

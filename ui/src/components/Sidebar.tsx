import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import {
  RANGE_LABELS,
  type DateRange,
  type PodFilterState,
} from '../features/pods/filters'

type SidebarProps = {
  filters: PodFilterState
  onChange: (patch: Partial<PodFilterState>) => void
  onClear: () => void
  libraryActive: boolean
  settingsActive: boolean
  onSettings: () => void
}

const RANGES: DateRange[] = ['all', 'today', 'week', 'month']

export function Sidebar({
  filters,
  onChange,
  onClear,
  libraryActive,
  settingsActive,
  onSettings,
}: SidebarProps) {
  const [open, setOpen] = useState(false)

  const categories = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.listCategories(),
  })
  const projects = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  })

  const isAll =
    libraryActive &&
    filters.category === '' &&
    filters.project === '' &&
    filters.range === 'all'

  const hasFilters =
    filters.query.trim() !== '' ||
    filters.category !== '' ||
    filters.project !== '' ||
    filters.range !== 'all'

  const activeCount =
    (filters.category !== '' ? 1 : 0) +
    (filters.project !== '' ? 1 : 0) +
    (filters.range !== 'all' ? 1 : 0)

  return (
    <aside className={`sidebar ${open ? 'is-open' : ''}`}>
      <button
        type="button"
        className="sidebar-toggle"
        aria-expanded={open}
        aria-controls="sidebar-body"
        onClick={() => setOpen((current) => !current)}
      >
        <span>Filters</span>
        <span className="sidebar-toggle-meta">
          {activeCount > 0 ? `${activeCount} active` : 'Browse'}
        </span>
        <span className="sidebar-chevron" aria-hidden="true">
          ⌄
        </span>
      </button>

      <div className="sidebar-body" id="sidebar-body">
        <div className="sidebar-section">
          <span className="sidebar-label">Library</span>
          <button
            type="button"
            className={`side-item ${isAll ? 'is-active' : ''}`}
            onClick={onClear}
          >
            <span className="side-icon" aria-hidden="true">
              ▦
            </span>
            All pods
          </button>
        </div>

        <div className="sidebar-section">
          <span className="sidebar-label">Categories</span>
          {(categories.data ?? []).map((category) => (
            <button
              key={category}
              type="button"
              className={`side-item ${
                libraryActive && filters.category === category ? 'is-active' : ''
              }`}
              onClick={() =>
                onChange({
                  category: filters.category === category ? '' : category,
                })
              }
            >
              <span className="side-dot" aria-hidden="true" />
              <span className="side-text">{category}</span>
            </button>
          ))}
          {categories.isPending && <span className="side-hint">Loading…</span>}
          {categories.isError && (
            <span className="side-hint">
              Couldn't load ·{' '}
              <button
                type="button"
                className="side-retry"
                onClick={() => void categories.refetch()}
              >
                retry
              </button>
            </span>
          )}
          {categories.isSuccess && categories.data.length === 0 && (
            <span className="side-hint">No categories yet</span>
          )}
        </div>

        <div className="sidebar-section">
          <span className="sidebar-label">Projects</span>
          {(projects.data ?? []).map((project) => (
            <button
              key={project}
              type="button"
              className={`side-item ${
                libraryActive && filters.project === project ? 'is-active' : ''
              }`}
              onClick={() =>
                onChange({
                  project: filters.project === project ? '' : project,
                })
              }
            >
              <span className="side-dot" aria-hidden="true" />
              <span className="side-text">{project}</span>
            </button>
          ))}
          {projects.isPending && <span className="side-hint">Loading…</span>}
          {projects.isError && (
            <span className="side-hint">
              Couldn't load ·{' '}
              <button
                type="button"
                className="side-retry"
                onClick={() => void projects.refetch()}
              >
                retry
              </button>
            </span>
          )}
          {projects.isSuccess && projects.data.length === 0 && (
            <span className="side-hint">No projects yet</span>
          )}
        </div>

        <div className="sidebar-section">
          <span className="sidebar-label">Time</span>
          {RANGES.map((range) => (
            <button
              key={range}
              type="button"
              className={`side-item ${
                libraryActive && filters.range === range ? 'is-active' : ''
              }`}
              onClick={() => onChange({ range })}
            >
              {RANGE_LABELS[range]}
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <button
            type="button"
            className="button button-ghost side-clear"
            onClick={onClear}
            disabled={!hasFilters}
          >
            Clear filters
          </button>
        </div>
      </div>

      <div className="sidebar-account">
        <div className="sidebar-user">
          <span className="sidebar-avatar" aria-hidden="true">
            OA
          </span>
          <span className="sidebar-user-text">
            <span className="sidebar-user-name">Ouwn Ch</span>
            <span className="sidebar-user-meta">Owner · local workspace</span>
          </span>
        </div>
        <button
          type="button"
          className={`side-item ${settingsActive ? 'is-active' : ''}`}
          onClick={onSettings}
        >
          <span className="side-icon" aria-hidden="true">
            ⚙
          </span>
          <span className="side-text">Settings</span>
        </button>
      </div>
    </aside>
  )
}

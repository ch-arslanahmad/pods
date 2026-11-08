import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import {
  RANGE_LABELS,
  type DateRange,
  type PodFilterState,
} from './filters'

type PodFiltersProps = {
  filters: PodFilterState
  onChange: (patch: Partial<PodFilterState>) => void
  onClear: () => void
}

export function PodFilters({ filters, onChange, onClear }: PodFiltersProps) {
  const categories = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.listCategories(),
  })
  const projects = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  })

  const hasFilters =
    filters.query.trim() !== '' ||
    filters.category !== '' ||
    filters.project !== '' ||
    filters.range !== 'all'

  return (
    <div className="filters">
      <div className="filter-row">
        <input
          type="search"
          className="search-input"
          placeholder="Search pods…"
          aria-label="Search pods"
          value={filters.query}
          onChange={(event) => onChange({ query: event.target.value })}
        />

        <select
          className="filter-select"
          aria-label="Filter by category"
          value={filters.category}
          onChange={(event) => onChange({ category: event.target.value })}
        >
          <option value="">All categories</option>
          {(categories.data ?? []).map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </select>

        <select
          className="filter-select"
          aria-label="Filter by project"
          value={filters.project}
          onChange={(event) => onChange({ project: event.target.value })}
        >
          <option value="">All projects</option>
          {(projects.data ?? []).map((project) => (
            <option key={project} value={project}>
              {project}
            </option>
          ))}
        </select>

        <select
          className="filter-select"
          aria-label="Filter by time"
          value={filters.range}
          onChange={(event) =>
            onChange({ range: event.target.value as DateRange })
          }
        >
          {(Object.keys(RANGE_LABELS) as DateRange[]).map((range) => (
            <option key={range} value={range}>
              {RANGE_LABELS[range]}
            </option>
          ))}
        </select>
      </div>

      {hasFilters && (
        <div className="active-filters">
          <span className="active-filters-label">Active:</span>
          {filters.query.trim() !== '' && (
            <button
              type="button"
              className="chip"
              onClick={() => onChange({ query: '' })}
            >
              “{filters.query.trim()}” <span aria-hidden="true">×</span>
            </button>
          )}
          {filters.category !== '' && (
            <button
              type="button"
              className="chip"
              onClick={() => onChange({ category: '' })}
            >
              {filters.category} <span aria-hidden="true">×</span>
            </button>
          )}
          {filters.project !== '' && (
            <button
              type="button"
              className="chip"
              onClick={() => onChange({ project: '' })}
            >
              {filters.project} <span aria-hidden="true">×</span>
            </button>
          )}
          {filters.range !== 'all' && (
            <button
              type="button"
              className="chip"
              onClick={() => onChange({ range: 'all' })}
            >
              {RANGE_LABELS[filters.range]} <span aria-hidden="true">×</span>
            </button>
          )}
          <button type="button" className="link-button" onClick={onClear}>
            Clear all
          </button>
        </div>
      )}
    </div>
  )
}

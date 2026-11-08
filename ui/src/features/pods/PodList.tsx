import { useState } from 'react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Pod } from '../../api/types'
import { Pagination } from '../../components/Pagination'
import { EmptyState, ErrorState, LoadingCards } from '../../components/States'
import { useDebounce } from '../../hooks/useDebounce'
import { formatDate, preview, toDateInput } from '../../lib/format'
import { emptyFilters, type DateRange, type PodFilterState } from './filters'
import { PodFilters } from './PodFilters'

const PAGE_SIZE = 9
const SEARCH_DEBOUNCE_MS = 300

function createdAfter(range: DateRange): string | undefined {
  if (range === 'all') return undefined
  const date = new Date()
  if (range === 'week') date.setDate(date.getDate() - 6)
  if (range === 'month') date.setDate(date.getDate() - 29)
  return toDateInput(date)
}

type PodListProps = {
  onCreate: () => void
  onOpen: (id: number) => void
}

export function PodList({ onCreate, onOpen }: PodListProps) {
  const [filters, setFilters] = useState<PodFilterState>(emptyFilters)
  const [offset, setOffset] = useState(0)
  const debouncedQuery = useDebounce(filters.query, SEARCH_DEBOUNCE_MS)

  const params = {
    query: debouncedQuery.trim() || undefined,
    category: filters.category || undefined,
    project: filters.project || undefined,
    created_after: createdAfter(filters.range),
    limit: PAGE_SIZE,
    offset,
  }

  const podsQuery = useQuery({
    queryKey: ['pods', params],
    queryFn: () => api.listPods(params),
    placeholderData: keepPreviousData,
  })

  const hasFilters =
    filters.query.trim() !== '' ||
    filters.category !== '' ||
    filters.project !== '' ||
    filters.range !== 'all'

  const patchFilters = (patch: Partial<PodFilterState>) => {
    setFilters((current) => ({ ...current, ...patch }))
    setOffset(0)
  }

  const clearFilters = () => {
    setFilters(emptyFilters)
    setOffset(0)
  }

  return (
    <section className="view">
      <div className="view-header">
        <div>
          <h1>All pods</h1>
          <p className="view-subtitle">
            {podsQuery.data
              ? `${podsQuery.data.total} ${podsQuery.data.total === 1 ? 'pod' : 'pods'}`
              : 'Loading…'}
          </p>
        </div>
        <button type="button" className="button button-primary" onClick={onCreate}>
          New pod
        </button>
      </div>

      <PodFilters
        filters={filters}
        onChange={patchFilters}
        onClear={clearFilters}
      />

      {podsQuery.isPending && <LoadingCards count={PAGE_SIZE} />}

      {podsQuery.isError && (
        <ErrorState
          message={podsQuery.error.message}
          onRetry={() => void podsQuery.refetch()}
        />
      )}

      {podsQuery.isSuccess && podsQuery.data.pods.length === 0 && (
        <EmptyState
          title="No pods match these filters"
          hint={
            hasFilters
              ? 'Try clearing a filter or widening the time range.'
              : 'Create your first pod to get started.'
          }
          action={
            hasFilters
              ? {
                  label: 'Clear filters',
                  onClick: clearFilters,
                }
              : { label: 'New pod', onClick: onCreate }
          }
        />
      )}

      {podsQuery.isSuccess && podsQuery.data.pods.length > 0 && (
        <>
          <div className="pod-grid">
            {podsQuery.data.pods.map((pod) => (
              <PodCard key={pod.id} pod={pod} onOpen={onOpen} />
            ))}
          </div>
          <Pagination
            offset={offset}
            limit={PAGE_SIZE}
            total={podsQuery.data.total}
            onChange={setOffset}
          />
        </>
      )}
    </section>
  )
}

function PodCard({ pod, onOpen }: { pod: Pod; onOpen: (id: number) => void }) {
  return (
    <button
      type="button"
      className="pod-card"
      onClick={() => onOpen(pod.id)}
    >
      <span className="pod-card-head">
        <span className="pod-category">{pod.category}</span>
        {pod.project ? (
          <span className="pod-project">{pod.project}</span>
        ) : (
          <span className="pod-project pod-project-none">standalone</span>
        )}
      </span>
      <span className="pod-name">{pod.pod_name}</span>
      <span className="pod-preview">{preview(pod.content)}</span>
      <span className="pod-meta">
        <span>created {formatDate(pod.created_at)}</span>
        {pod.updated_at !== pod.created_at && (
          <span>updated {formatDate(pod.updated_at)}</span>
        )}
      </span>
    </button>
  )
}

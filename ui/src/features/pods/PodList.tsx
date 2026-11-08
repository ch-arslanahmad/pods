import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Pod } from '../../api/types'
import { Pagination } from '../../components/Pagination'
import { EmptyState, ErrorState, LoadingCards } from '../../components/States'
import { useDebounce } from '../../hooks/useDebounce'
import { formatDate, preview, toDateInput } from '../../lib/format'
import { type DateRange, type PodFilterState } from './filters'

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
  filters: PodFilterState
  offset: number
  onOffsetChange: (offset: number) => void
  onCreate: () => void
  onClear: () => void
  onOpen: (id: number) => void
}

export function PodList({
  filters,
  offset,
  onOffsetChange,
  onCreate,
  onClear,
  onOpen,
}: PodListProps) {
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

  const total = podsQuery.data?.total

  return (
    <section className="view">
      <div className="content-header">
        <div>
          <p className="eyebrow">Library</p>
          <h1>{hasFilters ? 'Filtered pods' : 'All pods'}</h1>
          <p className="view-subtitle">
            {total === undefined
              ? 'Loading…'
              : hasFilters
                ? `${total} ${total === 1 ? 'pod matches' : 'pods match'} your filters`
                : `${total} ${total === 1 ? 'pod' : 'pods'} in your library`}
          </p>
        </div>
      </div>

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
              ? { label: 'Clear filters', onClick: onClear }
              : { label: 'New pod', onClick: onCreate }
          }
        />
      )}

      {podsQuery.isSuccess && podsQuery.data.pods.length > 0 && (
        <>
          <div className="pod-grid">
            {podsQuery.data.pods.map((pod, index) => (
              <PodCard key={pod.id} pod={pod} index={index} onOpen={onOpen} />
            ))}
          </div>
          <Pagination
            offset={offset}
            limit={PAGE_SIZE}
            total={podsQuery.data.total}
            onChange={onOffsetChange}
          />
        </>
      )}
    </section>
  )
}

function PodCard({
  pod,
  index,
  onOpen,
}: {
  pod: Pod
  index: number
  onOpen: (id: number) => void
}) {
  return (
    <button
      type="button"
      className="pod-card"
      style={{ animationDelay: `${index * 45}ms` }}
      onClick={() => onOpen(pod.id)}
    >
      <span className="pod-card-top">
        <span className="pod-category">{pod.category}</span>
        {pod.project ? (
          <span className="pod-project">{pod.project}</span>
        ) : (
          <span className="pod-project pod-project-none">standalone</span>
        )}
      </span>
      <span className="pod-name">{pod.pod_name}</span>
      <span className="pod-preview">{preview(pod.content)}</span>
      <span className="pod-card-foot">
        <span>{formatDate(pod.created_at)}</span>
        <span className="pod-open">Open →</span>
      </span>
    </button>
  )
}

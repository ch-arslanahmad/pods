import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { ErrorState } from '../../components/States'
import { formatDateTime, prettyContent } from '../../lib/format'

type PodDetailProps = {
  id: number
  onBack: () => void
  onEdit: (id: number) => void
}

export function PodDetail({ id, onBack, onEdit }: PodDetailProps) {
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState(false)

  const podQuery = useQuery({
    queryKey: ['pod', id],
    queryFn: () => api.getPod(id),
  })

  const deleteMutation = useMutation({
    mutationFn: () => api.deletePod(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['pods'] }),
        queryClient.invalidateQueries({ queryKey: ['categories'] }),
        queryClient.invalidateQueries({ queryKey: ['projects'] }),
      ])
      queryClient.removeQueries({ queryKey: ['pod', id] })
      onBack()
    },
  })

  if (podQuery.isPending) {
    return (
      <section className="view">
        <div className="detail-skeleton">
          <span className="skeleton skeleton-line skeleton-title" />
          <span className="skeleton skeleton-line" />
          <span className="skeleton skeleton-line skeleton-short" />
        </div>
      </section>
    )
  }

  if (podQuery.isError) {
    return (
      <section className="view">
        <button type="button" className="button button-ghost" onClick={onBack}>
          ← Back
        </button>
        <ErrorState
          message={podQuery.error.message}
          onRetry={() => void podQuery.refetch()}
        />
      </section>
    )
  }

  const pod = podQuery.data
  const content = prettyContent(pod.content)

  return (
    <section className="view">
      <div className="view-header">
        <button type="button" className="button button-ghost" onClick={onBack}>
          ← Back
        </button>
        <div className="detail-actions">
          <button type="button" className="button" onClick={() => onEdit(pod.id)}>
            Edit
          </button>
          <button
            type="button"
            className="button button-danger"
            onClick={() => setConfirming(true)}
          >
            Delete
          </button>
        </div>
      </div>

      <article className="detail">
        <h1>{pod.pod_name}</h1>
        <div className="detail-badges">
          <span className="pod-category">{pod.category}</span>
          {pod.project ? (
            <span className="pod-project">{pod.project}</span>
          ) : (
            <span className="pod-project pod-project-none">standalone</span>
          )}
        </div>

        <dl className="detail-meta">
          <div>
            <dt>ID</dt>
            <dd>{pod.id}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>{formatDateTime(pod.created_at)}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDateTime(pod.updated_at)}</dd>
          </div>
        </dl>

        <div className="detail-content">
          <h2>{content.isJson ? 'Content (JSON)' : 'Content'}</h2>
          {content.isJson ? (
            <pre>{content.text}</pre>
          ) : (
            <p className="detail-text">{content.text}</p>
          )}
        </div>
      </article>

      {confirming && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setConfirming(false)}
        >
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="delete-title">Delete this pod?</h2>
            <p>
              “{pod.pod_name}” will be soft-deleted and disappear from the list.
            </p>
            {deleteMutation.isError && (
              <p className="form-error">{deleteMutation.error.message}</p>
            )}
            <div className="dialog-actions">
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setConfirming(false)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button-danger"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

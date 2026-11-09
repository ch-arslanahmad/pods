import { useState, type FormEvent } from 'react'
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { api } from '../../api/client'
import type { CreatePodInput, Pod, UpdatePodPatch } from '../../api/types'
import { ErrorState } from '../../components/States'

type PodFormProps =
  | { mode: 'create'; onDone: (id: number) => void; onCancel: () => void }
  | {
      mode: 'edit'
      id: number
      onDone: (id: number) => void
      onCancel: () => void
    }

async function refreshAfterChange(queryClient: QueryClient, podId: number) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['pods'] }),
    queryClient.invalidateQueries({ queryKey: ['pod', podId] }),
    queryClient.invalidateQueries({ queryKey: ['categories'] }),
    queryClient.invalidateQueries({ queryKey: ['projects'] }),
    queryClient.invalidateQueries({ queryKey: ['pod-agents', podId] }),
    queryClient.invalidateQueries({ queryKey: ['agents'] }),
  ])
}

export function PodForm(props: PodFormProps) {
  const { onDone, onCancel } = props
  const editingId = props.mode === 'edit' ? props.id : null

  const podQuery = useQuery({
    queryKey: ['pod', editingId ?? 0],
    queryFn: () => api.getPod(editingId ?? 0),
    enabled: editingId !== null,
  })

  if (editingId !== null && podQuery.isPending) {
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

  if (editingId !== null && podQuery.isError) {
    return (
      <section className="view">
        <button type="button" className="button button-ghost" onClick={onCancel}>
          ← Back
        </button>
        <ErrorState
          message={podQuery.error.message}
          onRetry={() => void podQuery.refetch()}
        />
      </section>
    )
  }

  return (
    <PodFormFields
      editingId={editingId}
      initialPod={podQuery.data ?? null}
      onDone={onDone}
      onCancel={onCancel}
    />
  )
}

type PodFormFieldsProps = {
  editingId: number | null
  initialPod: Pod | null
  onDone: (id: number) => void
  onCancel: () => void
}

function PodFormFields({
  editingId,
  initialPod,
  onDone,
  onCancel,
}: PodFormFieldsProps) {
  const queryClient = useQueryClient()
  const [name, setName] = useState(initialPod?.pod_name ?? '')
  const [content, setContent] = useState(initialPod?.content ?? '')
  const [category, setCategory] = useState(initialPod?.category ?? 'general')
  const [project, setProject] = useState(initialPod?.project ?? '')
  const [touched, setTouched] = useState(false)

  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: () => api.listCategories(),
  })
  const projectsQuery = useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
  })
  const agentsQuery = useQuery({
    queryKey: ['agents'],
    queryFn: () => api.listAgents(),
  })
  const podAgentIdsQuery = useQuery({
    queryKey: ['pod-agents', editingId ?? 0],
    queryFn: () => api.listPodAgentIds(editingId ?? 0),
    enabled: editingId !== null,
  })

  const [agentIds, setAgentIds] = useState<number[] | null>(null)
  const selectedAgentIds = agentIds ?? podAgentIdsQuery.data ?? []

  const createMutation = useMutation({
    mutationFn: async (input: CreatePodInput) => {
      const pod = await api.createPod(input)
      await api.setPodAgents(pod.id, selectedAgentIds)
      return pod
    },
    onSuccess: async (pod) => {
      await refreshAfterChange(queryClient, pod.id)
      onDone(pod.id)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async (input: { id: number; patch: UpdatePodPatch }) => {
      const pod = await api.updatePod(input.id, input.patch)
      await api.setPodAgents(pod.id, selectedAgentIds)
      return pod
    },
    onSuccess: async (pod) => {
      await refreshAfterChange(queryClient, pod.id)
      onDone(pod.id)
    },
  })

  const nameError = name.trim() === '' ? 'Name is required' : null
  const contentError = content.trim() === '' ? 'Content is required' : null
  const isValid = nameError === null && contentError === null
  const pending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error ?? updateMutation.error

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (!isValid) return

    const payload = {
      pod_name: name.trim(),
      content: content.trim(),
      category: category.trim() || 'general',
      project: project.trim() || null,
    }

    if (editingId !== null) {
      updateMutation.mutate({ id: editingId, patch: payload })
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <section className="view">
      <div className="view-header">
        <div>
          <h1>{editingId !== null ? 'Edit pod' : 'New pod'}</h1>
          <p className="view-subtitle">
            {editingId !== null
              ? 'Update the fields you want to change.'
              : 'Capture something worth remembering.'}
          </p>
        </div>
      </div>

      <form className="pod-form" onSubmit={handleSubmit} noValidate>
        <label className="field">
          <span className="field-label">Name</span>
          <input
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="A short, searchable title"
          />
          {touched && nameError && <span className="field-error">{nameError}</span>}
        </label>

        <label className="field">
          <span className="field-label">Content</span>
          <textarea
            rows={10}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="Plain text, or a JSON object"
          />
          {touched && contentError && (
            <span className="field-error">{contentError}</span>
          )}
        </label>

        <div className="field-row">
          <label className="field">
            <span className="field-label">Category</span>
            <input
              type="text"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="general"
              list="category-options"
            />
            <datalist id="category-options">
              {(categoriesQuery.data ?? []).map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </label>

          <label className="field">
            <span className="field-label">Project</span>
            <input
              type="text"
              value={project}
              onChange={(event) => setProject(event.target.value)}
              placeholder="None (standalone)"
              list="project-options"
            />
            <datalist id="project-options">
              {(projectsQuery.data ?? []).map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </label>
        </div>

        <div className="field">
          <span className="field-label">AI agents</span>
          <span className="field-hint">
            Connect this pod to one or more agents. You can change this later.
          </span>

          {agentsQuery.isPending && (
            <span className="field-hint">Loading agents…</span>
          )}

          {agentsQuery.isError && (
            <span className="field-error">
              Couldn't load agents.{' '}
              <button
                type="button"
                className="side-retry"
                onClick={() => void agentsQuery.refetch()}
              >
                retry
              </button>
            </span>
          )}

          {agentsQuery.isSuccess && agentsQuery.data.length === 0 && (
            <span className="field-hint">
              No agents yet — add one from AI Agents.
            </span>
          )}

          {agentsQuery.isSuccess && agentsQuery.data.length > 0 && (
            <div className="agent-options">
              {agentsQuery.data.map((agent) => {
                const checked = selectedAgentIds.includes(agent.id)
                return (
                  <label
                    key={agent.id}
                    className={`agent-option ${checked ? 'is-on' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={
                        editingId !== null && podAgentIdsQuery.isPending
                      }
                      onChange={() =>
                        setAgentIds(
                          checked
                            ? selectedAgentIds.filter((id) => id !== agent.id)
                            : [...selectedAgentIds, agent.id],
                        )
                      }
                    />
                    <span className="agent-option-text">
                      <span className="agent-option-name">{agent.name}</span>
                      <span className="agent-option-meta">
                        {agent.provider} · {agent.model}
                      </span>
                    </span>
                  </label>
                )
              })}
            </div>
          )}
        </div>

        {mutationError && <p className="form-error">{mutationError.message}</p>}

        <div className="form-actions">
          <button
            type="button"
            className="button button-ghost"
            onClick={onCancel}
            disabled={pending}
          >
            Cancel
          </button>
          <button type="submit" className="button button-primary" disabled={pending}>
            {pending
              ? 'Saving…'
              : editingId !== null
                ? 'Save changes'
                : 'Create pod'}
          </button>
        </div>
      </form>
    </section>
  )
}

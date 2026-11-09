import { useState, type FormEvent } from 'react'
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Agent, AgentStatus, Pod } from '../../api/types'
import { EmptyState, ErrorState, LoadingCards } from '../../components/States'
import { formatDate } from '../../lib/format'

const PROVIDERS = ['Anthropic', 'OpenAI', 'Google', 'Ollama', 'Custom']

type AgentDraft = {
  name: string
  description: string
  provider: string
  model: string
  status: AgentStatus
  podIds: number[]
}

async function refreshAgentQueries(queryClient: QueryClient) {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: ['agents'] }),
    queryClient.invalidateQueries({ queryKey: ['pod-agents'] }),
  ])
}

export function Agents({ onBack }: { onBack: () => void }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState<Agent | 'new' | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<Agent | null>(null)

  const agentsQuery = useQuery({
    queryKey: ['agents'],
    queryFn: () => api.listAgents(),
  })
  const podsQuery = useQuery({
    queryKey: ['pods', 'agent-picker'],
    queryFn: () => api.listPods({ limit: 200 }),
  })

  const createMutation = useMutation({
    mutationFn: async (draft: AgentDraft) => {
      const agent = await api.createAgent({
        name: draft.name,
        description: draft.description,
        provider: draft.provider,
        model: draft.model,
        status: draft.status,
      })
      await api.setAgentPods(agent.id, draft.podIds)
      return agent
    },
    onSuccess: async () => {
      await refreshAgentQueries(queryClient)
      setEditing(null)
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, draft }: { id: number; draft: AgentDraft }) => {
      const agent = await api.updateAgent(id, {
        name: draft.name,
        description: draft.description,
        provider: draft.provider,
        model: draft.model,
        status: draft.status,
      })
      await api.setAgentPods(id, draft.podIds)
      return agent
    },
    onSuccess: async () => {
      await refreshAgentQueries(queryClient)
      setEditing(null)
    },
  })

  const statusMutation = useMutation({
    mutationFn: (agent: Agent) =>
      api.updateAgent(agent.id, {
        status: agent.status === 'active' ? 'paused' : 'active',
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agents'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteAgent(id),
    onSuccess: async () => {
      await refreshAgentQueries(queryClient)
      setConfirmDelete(null)
    },
  })

  const agents = agentsQuery.data ?? []
  const pods = podsQuery.data?.pods ?? []
  const podsById = new Map(pods.map((pod) => [pod.id, pod]))
  const connectionCount = agents.reduce(
    (total, agent) => total + agent.pod_ids.length,
    0,
  )
  const pending = createMutation.isPending || updateMutation.isPending
  const mutationError = createMutation.error ?? updateMutation.error

  function handleSave(draft: AgentDraft) {
    if (editing === 'new') {
      createMutation.mutate(draft)
    } else if (editing) {
      updateMutation.mutate({ id: editing.id, draft })
    }
  }

  return (
    <section className="view agents-view">
      <div className="view-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h1>AI agents</h1>
          <p className="view-subtitle">
            {agentsQuery.isSuccess
              ? `${agents.length} ${
                  agents.length === 1 ? 'agent' : 'agents'
                } · ${connectionCount} pod ${
                  connectionCount === 1 ? 'connection' : 'connections'
                } · one pod can connect to many agents`
              : 'Connect pods to the agents that work on them.'}
          </p>
        </div>
        <div className="agents-header-actions">
          <button type="button" className="button button-ghost" onClick={onBack}>
            ← Back to pods
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={() => setEditing('new')}
          >
            + Add agent
          </button>
        </div>
      </div>

      {agentsQuery.isPending && <LoadingCards count={4} />}

      {agentsQuery.isError && (
        <ErrorState
          message={agentsQuery.error.message}
          onRetry={() => void agentsQuery.refetch()}
        />
      )}

      {agentsQuery.isSuccess && agents.length === 0 && (
        <EmptyState
          title="No AI agents yet"
          hint="Add an agent, then connect it to one or more pods."
          action={{ label: 'Add agent', onClick: () => setEditing('new') }}
        />
      )}

      {agentsQuery.isSuccess && agents.length > 0 && (
        <div className="agent-grid">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              agent={agent}
              podsById={podsById}
              statusPending={statusMutation.isPending}
              onEdit={() => setEditing(agent)}
              onToggleStatus={() => statusMutation.mutate(agent)}
              onDelete={() => setConfirmDelete(agent)}
            />
          ))}
        </div>
      )}

      {editing !== null && (
        <AgentDialog
          key={editing === 'new' ? 'new' : editing.id}
          agent={editing === 'new' ? null : editing}
          pods={pods}
          podsPending={podsQuery.isPending}
          pending={pending}
          error={mutationError?.message ?? null}
          onClose={() => setEditing(null)}
          onSave={handleSave}
        />
      )}

      {confirmDelete && (
        <div
          className="dialog-backdrop"
          role="presentation"
          onClick={() => setConfirmDelete(null)}
        >
          <div
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="remove-agent-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="remove-agent-title">Remove agent?</h2>
            <p>
              “{confirmDelete.name}” will be removed. Its pod connections will be
              cleared; the pods themselves stay.
            </p>
            {deleteMutation.isError && (
              <p className="form-error">{deleteMutation.error.message}</p>
            )}
            <div className="dialog-actions">
              <button
                type="button"
                className="button button-ghost"
                onClick={() => setConfirmDelete(null)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="button button-danger"
                onClick={() => deleteMutation.mutate(confirmDelete.id)}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? 'Removing…' : 'Remove'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function AgentCard({
  agent,
  podsById,
  statusPending,
  onEdit,
  onToggleStatus,
  onDelete,
}: {
  agent: Agent
  podsById: Map<number, Pod>
  statusPending: boolean
  onEdit: () => void
  onToggleStatus: () => void
  onDelete: () => void
}) {
  const connectedPods = agent.pod_ids
    .map((id) => ({ id, pod: podsById.get(id) }))
    .filter((item): item is { id: number; pod: Pod } => item.pod !== undefined)
  const shown = connectedPods.slice(0, 3)
  const extra = connectedPods.length - shown.length

  return (
    <article
      className={`agent-card ${agent.status === 'paused' ? 'is-paused' : ''}`}
    >
      <div className="agent-card-head">
        <div className="agent-identity">
          <span className="agent-avatar" aria-hidden="true">
            {initials(agent.name)}
          </span>
          <div>
            <h2 className="agent-name">{agent.name}</h2>
            <p className="agent-meta">
              {agent.provider} · {agent.model}
            </p>
          </div>
        </div>
        <span
          className={`status-pill ${
            agent.status === 'active' ? 'is-on' : 'is-off'
          }`}
        >
          {agent.status}
        </span>
      </div>

      <p className="agent-description">
        {agent.description || 'No description yet.'}
      </p>

      <div className="agent-pods">
        <span className="agent-pods-label">
          Connected pods ({connectedPods.length})
        </span>
        <div className="chip-row">
          {shown.map(({ id, pod }) => (
            <span className="agent-chip" key={id}>
              {pod.pod_name}
            </span>
          ))}
          {extra > 0 && (
            <span className="agent-chip agent-chip-more">+{extra} more</span>
          )}
          {connectedPods.length === 0 && (
            <span className="agent-empty">No pods connected</span>
          )}
        </div>
      </div>

      <div className="agent-card-foot">
        <span className="agent-added">Added {formatDate(agent.created_at)}</span>
        <div className="agent-card-actions">
          <button type="button" className="button button-ghost" onClick={onEdit}>
            Edit
          </button>
          <button
            type="button"
            className="button button-ghost"
            onClick={onToggleStatus}
            disabled={statusPending}
          >
            {agent.status === 'active' ? 'Pause' : 'Activate'}
          </button>
          <button
            type="button"
            className="button button-danger"
            onClick={onDelete}
          >
            Remove
          </button>
        </div>
      </div>
    </article>
  )
}

function AgentDialog({
  agent,
  pods,
  podsPending,
  pending,
  error,
  onClose,
  onSave,
}: {
  agent: Agent | null
  pods: Pod[]
  podsPending: boolean
  pending: boolean
  error: string | null
  onClose: () => void
  onSave: (draft: AgentDraft) => void
}) {
  const [name, setName] = useState(agent?.name ?? '')
  const [description, setDescription] = useState(agent?.description ?? '')
  const [provider, setProvider] = useState(agent?.provider ?? PROVIDERS[0])
  const [model, setModel] = useState(agent?.model ?? '')
  const [status, setStatus] = useState<AgentStatus>(agent?.status ?? 'active')
  const [podIds, setPodIds] = useState<number[]>(agent?.pod_ids ?? [])
  const [podFilter, setPodFilter] = useState('')
  const [touched, setTouched] = useState(false)

  const nameError = name.trim() === '' ? 'Name is required' : null
  const modelError = model.trim() === '' ? 'Model is required' : null
  const isValid = nameError === null && modelError === null

  const needle = podFilter.trim().toLowerCase()
  const visiblePods = needle
    ? pods.filter((pod) =>
        `${pod.pod_name} ${pod.category} ${pod.project ?? ''}`
          .toLowerCase()
          .includes(needle),
      )
    : pods

  function togglePod(id: number) {
    setPodIds((current) =>
      current.includes(id)
        ? current.filter((podId) => podId !== id)
        : [...current, id],
    )
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setTouched(true)
    if (!isValid) return
    onSave({
      name: name.trim(),
      description: description.trim(),
      provider,
      model: model.trim(),
      status,
      podIds,
    })
  }

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div
        className="dialog dialog-agent"
        role="dialog"
        aria-modal="true"
        aria-labelledby="agent-dialog-title"
        onClick={(event) => event.stopPropagation()}
      >
        <form className="settings-form" onSubmit={handleSubmit} noValidate>
          <h2 id="agent-dialog-title">
            {agent ? 'Edit agent' : 'Add agent'}
          </h2>
          <p className="dialog-intro">
            Connect this agent to any number of pods. A pod can connect to
            several agents at once.
          </p>

          <label className="field">
            <span className="field-label">Name</span>
            <input
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Claude Code"
            />
            {touched && nameError && (
              <span className="field-error">{nameError}</span>
            )}
          </label>

          <div className="field-row">
            <label className="field">
              <span className="field-label">Provider</span>
              <select
                value={provider}
                onChange={(event) => setProvider(event.target.value)}
              >
                {PROVIDERS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field-label">Model</span>
              <input
                type="text"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                placeholder="claude-sonnet-4.5"
              />
              {touched && modelError && (
                <span className="field-error">{modelError}</span>
              )}
            </label>

            <label className="field">
              <span className="field-label">Status</span>
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as AgentStatus)
                }
              >
                <option value="active">Active</option>
                <option value="paused">Paused</option>
              </select>
            </label>
          </div>

          <label className="field">
            <span className="field-label">Description</span>
            <textarea
              rows={3}
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="What does this agent work on?"
            />
          </label>

          <div className="field">
            <span className="field-label">Connected pods</span>
            <span className="field-hint">
              {podIds.length} of {pods.length} pods selected. A pod can connect
              to multiple agents.
            </span>
            <input
              type="search"
              className="agent-pod-search"
              value={podFilter}
              onChange={(event) => setPodFilter(event.target.value)}
              placeholder="Filter pods by name, category, or project…"
            />
            <div className="agent-pod-list">
              {podsPending && <span className="field-hint">Loading pods…</span>}
              {!podsPending && visiblePods.length === 0 && (
                <span className="field-hint">No pods match that filter.</span>
              )}
              {visiblePods.map((pod) => {
                const checked = podIds.includes(pod.id)
                return (
                  <label
                    key={pod.id}
                    className={`pick-row ${checked ? 'is-on' : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => togglePod(pod.id)}
                    />
                    <span className="pick-text">
                      <strong>{pod.pod_name}</strong>
                      <small>
                        {pod.category}
                        {pod.project ? ` · ${pod.project}` : ''}
                      </small>
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {error && <p className="form-error">{error}</p>}

          <div className="dialog-actions">
            <button
              type="button"
              className="button button-ghost"
              onClick={onClose}
              disabled={pending}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button button-primary"
              disabled={pending}
            >
              {pending
                ? 'Saving…'
                : agent
                  ? 'Save changes'
                  : 'Add agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}

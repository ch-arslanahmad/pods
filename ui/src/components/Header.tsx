import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

type HeaderProps = {
  query: string
  onQueryChange: (query: string) => void
  onCreate: () => void
  onHome: () => void
  onAgents: () => void
  agentsActive: boolean
}

export function Header({
  query,
  onQueryChange,
  onCreate,
  onHome,
  onAgents,
  agentsActive,
}: HeaderProps) {
  const searchRef = useRef<HTMLInputElement>(null)

  const health = useQuery({
    queryKey: ['ping'],
    queryFn: () => api.ping(),
    refetchInterval: 30_000,
    retry: false,
  })

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key !== '/' || event.metaKey || event.ctrlKey || event.altKey) {
        return
      }
      const target = event.target as HTMLElement | null
      if (
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.tagName === 'SELECT' ||
        target?.isContentEditable
      ) {
        return
      }
      event.preventDefault()
      searchRef.current?.focus()
    }

    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

  const status = health.isSuccess
    ? 'online'
    : health.isError
      ? 'offline'
      : 'checking'
  const mode =
    import.meta.env.VITE_API_MODE === 'http' ? 'live api' : 'seed'

  return (
    <header className="topbar">
      <button type="button" className="brand" onClick={onHome}>
        <span className="brand-mark" aria-hidden="true">
          <span />
        </span>
        <span className="brand-text">
          <span className="brand-name">Pods</span>
          <span className="brand-sub">knowledge dashboard</span>
        </span>
      </button>

      <nav className="topnav" aria-label="Primary">
        <button type="button" className="topnav-link" onClick={onHome}>
          Dashboard
        </button>
        <a
          className="topnav-link"
          href="https://github.com/ch-arslanahmad/pods"
          target="_blank"
          rel="noreferrer"
        >
          Repository
        </a>
      </nav>

      <div className="topbar-search">
        <span className="search-icon" aria-hidden="true">
          ⌕
        </span>
        <input
          ref={searchRef}
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search pods…"
          aria-label="Search pods"
        />
        <kbd>/</kbd>
      </div>

      <div className="topbar-actions">
        <button
          type="button"
          className={`agents-link ${agentsActive ? 'is-active' : ''}`}
          onClick={onAgents}
          aria-label="AI Agents"
        >
          <span className="agents-link-icon" aria-hidden="true">
            ✦
          </span>
          <span className="agents-link-label">AI Agents</span>
        </button>
        <span className={`health health-${status}`}>
          <span className="health-dot" aria-hidden="true" />
          {status}
        </span>
        <span className="mode-badge">{mode}</span>
        <button type="button" className="button button-primary" onClick={onCreate}>
          + New pod
        </button>
      </div>
    </header>
  )
}

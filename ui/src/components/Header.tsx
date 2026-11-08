import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'

type HeaderProps = {
  onHome: () => void
}

export function Header({ onHome }: HeaderProps) {
  const health = useQuery({
    queryKey: ['ping'],
    queryFn: () => api.ping(),
    refetchInterval: 30_000,
    retry: false,
  })

  const status = health.isSuccess
    ? 'online'
    : health.isError
      ? 'offline'
      : 'checking'
  const mode =
    import.meta.env.VITE_API_MODE === 'http' ? 'live api' : 'seed data'

  return (
    <header className="app-header">
      <button type="button" className="brand" onClick={onHome}>
        <span className="brand-dot" aria-hidden="true" />
        <span className="brand-name">pods</span>
      </button>
      <div className="header-meta">
        <span className={`health health-${status}`}>
          <span className="health-dot" aria-hidden="true" />
          {status}
        </span>
        <span className="mode-badge">{mode}</span>
      </div>
    </header>
  )
}

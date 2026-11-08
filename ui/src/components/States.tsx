type LoadingCardsProps = {
  count?: number
}

export function LoadingCards({ count = 6 }: LoadingCardsProps) {
  return (
    <div className="pod-grid" aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <div className="pod-card skeleton-card" key={index}>
          <span className="skeleton skeleton-line skeleton-title" />
          <span className="skeleton skeleton-line" />
          <span className="skeleton skeleton-line skeleton-short" />
        </div>
      ))}
    </div>
  )
}

type ErrorStateProps = {
  message: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state state-error" role="alert">
      <h2>Something went wrong</h2>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}

type EmptyStateProps = {
  title: string
  hint: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ title, hint, action }: EmptyStateProps) {
  return (
    <div className="state state-empty">
      <h2>{title}</h2>
      <p>{hint}</p>
      {action && (
        <button type="button" className="button" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  )
}

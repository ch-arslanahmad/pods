type PaginationProps = {
  offset: number
  limit: number
  total: number
  onChange: (offset: number) => void
}

export function Pagination({
  offset,
  limit,
  total,
  onChange,
}: PaginationProps) {
  const start = total === 0 ? 0 : offset + 1
  const end = Math.min(offset + limit, total)

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="pagination-count">
        Showing {start}–{end} of {total}
      </span>
      <div className="pagination-actions">
        <button
          type="button"
          className="button button-ghost"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
        >
          Previous
        </button>
        <button
          type="button"
          className="button button-ghost"
          disabled={end >= total}
          onClick={() => onChange(offset + limit)}
        >
          Next
        </button>
      </div>
    </nav>
  )
}

// Timestamps arrive as ISO-8601 in seed mode but as "YYYY-MM-DD HH:MM:SS" from
// SQLite, so normalise before parsing.
function parseTimestamp(value: string): Date {
  return new Date(value.includes('T') ? value : value.replace(' ', 'T'))
}

export function formatDate(value: string): string {
  const date = parseTimestamp(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function formatDateTime(value: string): string {
  const date = parseTimestamp(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function prettyContent(content: string): { isJson: boolean; text: string } {
  try {
    const parsed: unknown = JSON.parse(content)
    if (parsed !== null && typeof parsed === 'object') {
      return { isJson: true, text: JSON.stringify(parsed, null, 2) }
    }
  } catch {
    // Not JSON — show the raw text.
  }
  return { isJson: false, text: content }
}

export function toDateInput(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

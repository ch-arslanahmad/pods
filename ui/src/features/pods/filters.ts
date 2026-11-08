export type DateRange = 'all' | 'today' | 'week' | 'month'

export type PodFilterState = {
  query: string
  category: string
  project: string
  range: DateRange
}

export const emptyFilters: PodFilterState = {
  query: '',
  category: '',
  project: '',
  range: 'all',
}

export const RANGE_LABELS: Record<DateRange, string> = {
  all: 'All time',
  today: 'Today',
  week: 'This week',
  month: 'This month',
}

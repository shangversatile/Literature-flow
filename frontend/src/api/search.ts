import type { PaperSearchResult, SearchSaveResponse } from '../types'

const API_BASE = 'http://127.0.0.1:8000'

async function readableError(response: Response): Promise<Error> {
  const fallback = `${response.status} ${response.statusText}`.trim()

  try {
    const data: unknown = await response.json()
    if (data && typeof data === 'object' && 'detail' in data) {
      const detail = (data as { detail: unknown }).detail
      if (typeof detail === 'string') return new Error(detail)
      return new Error(JSON.stringify(detail))
    }
    return new Error(JSON.stringify(data))
  } catch {
    return new Error(fallback || 'Request failed')
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    throw await readableError(response)
  }

  return response.json() as Promise<T>
}

export function searchAll(query: string, limit: number): Promise<PaperSearchResult[]> {
  const params = new URLSearchParams({
    query,
    limit: String(limit),
  })
  return request<PaperSearchResult[]>(`${API_BASE}/search/all?${params.toString()}`)
}

export function saveAll(query: string, limit: number): Promise<SearchSaveResponse> {
  return request<SearchSaveResponse>(`${API_BASE}/search/all/save`, {
    method: 'POST',
    body: JSON.stringify({ query, limit }),
  })
}

export function saveSelectedPapers(
  papers: PaperSearchResult[],
  query = '',
): Promise<SearchSaveResponse> {
  return request<SearchSaveResponse>(`${API_BASE}/search/save-selected`, {
    method: 'POST',
    body: JSON.stringify({ query, papers }),
  })
}

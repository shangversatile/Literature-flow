import type { PaperTopicsResponse, ResearchTopic } from '../types'

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

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

export function fetchTopics(): Promise<ResearchTopic[]> {
  return request<ResearchTopic[]>('/topics')
}

export function seedDefaultTopics(): Promise<ResearchTopic[]> {
  return request<ResearchTopic[]>('/topics/seed-defaults', { method: 'POST' })
}

export function fetchPaperTopics(paperId: number): Promise<PaperTopicsResponse> {
  return request<PaperTopicsResponse>(`/papers/${paperId}/topics`)
}

export function updatePaperTopics(
  paperId: number,
  topicNames: string[],
): Promise<PaperTopicsResponse> {
  return request<PaperTopicsResponse>(`/papers/${paperId}/topics`, {
    method: 'PUT',
    body: JSON.stringify({ topic_names: topicNames }),
  })
}

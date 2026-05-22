import type {
  AskPayload,
  AskResponse,
  ExtractPayload,
  Extraction,
  Paper,
  PaperUpdatePayload,
  ProcessPaperRequest,
  ProcessPaperResponse,
} from '../types'

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

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function fetchPapers(): Promise<Paper[]> {
  return request<Paper[]>('/papers')
}

export function fetchPaper(id: number): Promise<Paper> {
  return request<Paper>(`/papers/${id}`)
}

export function updatePaper(id: number, payload: PaperUpdatePayload): Promise<Paper> {
  return request<Paper>(`/papers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function resolvePdf(id: number): Promise<Paper> {
  return request<Paper>(`/papers/${id}/resolve-pdf`, { method: 'POST' })
}

export function downloadPdf(id: number): Promise<Paper> {
  return request<Paper>(`/papers/${id}/download-pdf`, { method: 'POST' })
}

export function parsePdf(id: number): Promise<unknown> {
  return request<unknown>(`/papers/${id}/parse-pdf`, { method: 'POST' })
}

export function extractPaper(id: number, payload: ExtractPayload): Promise<unknown> {
  return request<unknown>(`/papers/${id}/extract`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function fetchLatestExtraction(id: number): Promise<Extraction> {
  return request<Extraction>(`/papers/${id}/latest-extraction`)
}

export function askPaper(id: number, payload: AskPayload): Promise<AskResponse> {
  return request<AskResponse>(`/papers/${id}/ask`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function processPaper(
  id: number,
  payload: ProcessPaperRequest,
): Promise<ProcessPaperResponse> {
  return request<ProcessPaperResponse>(`/papers/${id}/process`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

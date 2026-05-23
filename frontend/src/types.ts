export interface Paper {
  id: number
  title: string
  authors?: string[]
  normalized_title: string | null
  doi: string | null
  year: number | null
  venue: string | null
  abstract: string | null
  citation_count: number
  pdf_url: string | null
  local_pdf_path: string | null
  status: string
  created_at: string
  updated_at: string
  relevance_score?: number | null
  authority_score?: number | null
  frontier_score?: number | null
  accessibility_score?: number | null
  final_score?: number | null
  quality_score?: number | null
  sources?: string[]
  venue_normalized?: string | null
  venue_type?: string | null
  publication_type?: string | null
  publication_status?: string | null
  rank_source?: string | null
  rank_value?: string | null
  rank_note?: string | null
  venue_rank?: string | null
  venue_rank_source?: string | null
  venue_rank_note?: string | null
  topics?: string[]
}

export interface ResearchTopic {
  id: number
  name: string
  normalized_name: string
  description: string | null
  created_at: string
}

export interface PaperTopicsResponse {
  paper_id: number
  topics: ResearchTopic[]
}

export interface LibraryAskPayload {
  question: string
  mode: 'mock' | 'openai'
  top_k: number
  topic?: string | null
}

export interface LibraryEvidenceChunk {
  paper_id: number
  paper_title: string
  paper_year: number | null
  paper_venue: string | null
  chunk_index: number
  text: string
  score: number
  page_start: number | null
  page_end: number | null
  section_title: string | null
  matched_terms: string[]
  retrieval_method: string
}

export interface LibraryAskResponse {
  question: string
  mode: string
  topic: string | null
  answer: string
  evidence_chunks: LibraryEvidenceChunk[]
  evidence_count: number
}

export interface ReadingPriority {
  label: string
  level: string
  reason: string
}

export interface Extraction {
  id: number
  paper_id: number
  model_name: string
  prompt_version: string
  extracted_json: string
  raw_llm_output: string | null
  human_edited: boolean
  created_at: string
}

export interface EvidenceChunk {
  chunk_index: number
  text: string
  score: number
  page_start: number | null
  page_end: number | null
  section_title?: string | null
  matched_terms?: string[]
  retrieval_method?: string
}

export interface AskResponse {
  paper_id: number
  question: string
  mode: string
  answer: string
  evidence_chunks: EvidenceChunk[]
  evidence_chunk_indices: number[]
}

export interface PaperAsset {
  id: number
  paper_id: number
  asset_type: string
  asset_index: number
  page_number: number | null
  caption: string | null
  local_path: string | null
  text_content: string | null
  created_at: string
}

export interface ExtractAssetsResponse {
  paper_id: number
  asset_count: number
  page_image_count: number
  figure_caption_count: number
  table_caption_count: number
  status: string
}

export interface WorkspaceResponse {
  paper_id: number
  workspace_path: string
  pdf_path: string | null
  markdown_path: string
  bibtex_path: string
  metadata_path: string
  assets_path: string | null
  exists?: boolean
  pdf_exists?: boolean
  markdown_exists?: boolean
  bibtex_exists?: boolean
  metadata_exists?: boolean
  assets_exists?: boolean
}

export type PaperUpdatePayload = Partial<
  Pick<
    Paper,
    | 'title'
    | 'doi'
    | 'year'
    | 'venue'
    | 'abstract'
    | 'citation_count'
    | 'pdf_url'
    | 'local_pdf_path'
    | 'status'
  >
>

export interface ExtractPayload {
  mode: 'mock' | 'openai'
  user_topic?: string | null
  max_chunks: number
}

export interface AskPayload {
  question: string
  mode: 'mock' | 'openai'
  top_k: number
}

export interface ProcessPaperRequest {
  resolve_pdf: boolean
  download_pdf: boolean
  parse_pdf: boolean
  extract: boolean
  extract_assets?: boolean
  save_workspace?: boolean
  extract_mode: 'mock' | 'openai'
  user_topic?: string | null
  max_chunks: number
}

export interface ProcessStepResult {
  name: string
  status: 'success' | 'skipped' | 'failed'
  message: string
}

export interface ProcessPaperResponse {
  paper_id: number
  steps: ProcessStepResult[]
  final_status: string
}

export interface BatchProcessRequest {
  paper_ids: number[]
  resolve_pdf: boolean
  download_pdf: boolean
  parse_pdf: boolean
  extract: boolean
  extract_assets: boolean
  save_workspace: boolean
  extract_mode: 'mock' | 'openai'
  user_topic?: string | null
  max_chunks: number
}

export interface BatchPaperResult {
  paper_id: number
  title: string | null
  status: string
  final_status: string | null
  steps: ProcessStepResult[]
  error: string | null
}

export interface BatchProcessResponse {
  total: number
  succeeded: number
  failed: number
  skipped: number
  results: BatchPaperResult[]
}

export interface SearchSaveResponse {
  query: string
  inserted_count: number
  skipped_count: number
  papers: Paper[]
}

export interface PaperSearchResult {
  title: string
  abstract: string | null
  year: number | null
  venue: string | null
  doi: string | null
  citation_count: number
  authors: string[]
  url: string | null
  external_ids: Record<string, unknown>
  open_access_pdf_url: string | null
  source: string
  sources: string[]
  relevance_score: number | null
  authority_score: number | null
  frontier_score: number | null
  accessibility_score: number | null
  final_score: number | null
  quality_score: number | null
  venue_normalized: string | null
  venue_type: string | null
  publication_type: string | null
  publication_status: string | null
  rank_source: string | null
  rank_value: string | null
  rank_note: string | null
  venue_rank: string | null
  venue_rank_source: string | null
  venue_rank_note: string | null
}

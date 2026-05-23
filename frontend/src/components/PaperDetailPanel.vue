<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  deletePaper,
  downloadPdf,
  exportBibtex,
  exportMarkdown,
  extractAssets,
  extractPaper,
  fetchAssets,
  fetchLatestExtraction,
  parsePdf,
  previewMarkdown,
  processPaper,
  refreshPaperEnrichment,
  resolvePdf,
  saveWorkspace,
  updatePaper,
} from '../api/papers'
import { updatePaperTopics } from '../api/topics'
import type {
  ExtractAssetsResponse,
  Extraction,
  Paper,
  PaperAsset,
  ProcessPaperResponse,
  RefreshEnrichmentResponse,
  ResearchTopic,
  WorkspaceResponse,
} from '../types'
import { computeReadingPriority, getPriorityMeaning, priorityBadgeClass } from '../utils/paperQuality'

const API_BASE = 'http://127.0.0.1:8000'

const props = defineProps<{
  paper: Paper | null
  topics: ResearchTopic[]
}>()

const emit = defineEmits<{
  refresh: []
  deleted: [message?: string]
}>()

const loadingAction = ref<string | null>(null)
const errorMessage = ref('')
const successMessage = ref('')
const latestExtraction = ref<Extraction | null>(null)
const processResult = ref<ProcessPaperResponse | null>(null)
const refreshResult = ref<RefreshEnrichmentResponse | null>(null)
const assetResult = ref<ExtractAssetsResponse | null>(null)
const workspaceResult = ref<WorkspaceResponse | null>(null)
const assets = ref<PaperAsset[]>([])
const showPdfPreview = ref(false)
const markdownPreview = ref('')
const markdownPreviewLoaded = ref(false)
const extractionMode = ref<'mock' | 'openai'>('openai')
const topicInput = ref('')
const deleteLocalFiles = ref(false)
const manualPdfUrl = ref('')

const extractionData = computed<Record<string, unknown> | null>(() => {
  if (!latestExtraction.value) return null
  try {
    const data = JSON.parse(latestExtraction.value.extracted_json) as unknown
    return data && typeof data === 'object' && !Array.isArray(data)
      ? (data as Record<string, unknown>)
      : null
  } catch {
    return null
  }
})

const pdfPreviewSrc = computed(() => {
  const path = props.paper?.local_pdf_path
  if (!path) return ''
  const normalized = path.replace(/\\/g, '/')
  const match = normalized.match(/(?:^|\/)storage\/pdfs\/(.+)$/)
  if (!match) return ''
  return `${API_BASE}/static/pdfs/${match[1].split('/').map(encodeURIComponent).join('/')}`
})

const pageImages = computed(() => assets.value.filter((asset) => asset.asset_type === 'page_image'))
const figureCaptions = computed(() => assets.value.filter((asset) => asset.asset_type === 'figure_caption'))
const tableAssets = computed(() =>
  assets.value.filter((asset) => asset.asset_type === 'table_caption' || asset.asset_type === 'table_text'),
)
const shownPageImages = computed(() => pageImages.value.slice(0, 3))
const summaryItems = computed(() => [
  { title: 'Research Background', key: 'research_background' },
  { title: 'Research Problem', key: 'research_problem' },
  { title: 'Methodology', key: 'methodology' },
  { title: 'Contributions', key: 'main_contributions' },
  { title: 'Limitations', key: 'limitations' },
  { title: 'Relevance', key: 'relevance_to_user_topic' },
])
const readingPriority = computed(() => {
  return props.paper ? computeReadingPriority(props.paper) : null
})
const readingPriorityMeaning = computed(() => {
  return readingPriority.value ? getPriorityMeaning(readingPriority.value.label) : ''
})

watch(
  () => props.paper?.id,
  () => {
    errorMessage.value = ''
    successMessage.value = ''
    latestExtraction.value = null
    processResult.value = null
    refreshResult.value = null
    assetResult.value = null
    workspaceResult.value = null
    assets.value = []
    loadingAction.value = null
    showPdfPreview.value = false
    markdownPreview.value = ''
    markdownPreviewLoaded.value = false
    topicInput.value = props.paper?.topics?.join(', ') || ''
    deleteLocalFiles.value = false
    manualPdfUrl.value = props.paper?.pdf_url || ''
  },
  { immediate: true },
)

async function runAction(label: string, action: () => Promise<unknown>, shouldRefresh = true) {
  if (!props.paper) return

  loadingAction.value = label
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const result = await action()
    if (label === 'latest') {
      latestExtraction.value = result as Extraction
    }
    if (label === 'process') {
      processResult.value = result as ProcessPaperResponse
    }
    if (label === 'refresh-enrichment') {
      refreshResult.value = result as RefreshEnrichmentResponse
    }
    if (label === 'assets') {
      assets.value = result as PaperAsset[]
    }
    if (label === 'extract-assets') {
      assetResult.value = result as ExtractAssetsResponse
    }
    if (label === 'save-workspace') {
      workspaceResult.value = result as WorkspaceResponse
    }
    if (label === 'preview-markdown') {
      markdownPreview.value = result as string
      markdownPreviewLoaded.value = true
    }
    if (shouldRefresh) emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
    if (label === 'preview-markdown') {
      markdownPreviewLoaded.value = false
    }
  } finally {
    loadingAction.value = null
  }
}

async function deleteSelectedPaper() {
  const id = props.paper?.id
  if (!id) return

  const confirmed = window.confirm(
    '删除数据库记录后，该论文会从 Library 中消失。\n\n如果勾选 Also delete local files，也会删除本地 PDF/assets/workspace。\n\n确定要删除这篇论文吗？',
  )
  if (!confirmed) return

  loadingAction.value = 'delete-paper'
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const result = await deletePaper(id, deleteLocalFiles.value)
    successMessage.value = result.message || 'Paper deleted.'
    emit('deleted', successMessage.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to delete paper'
  } finally {
    loadingAction.value = null
  }
}

async function saveManualPdfUrl() {
  const id = props.paper?.id
  if (!id) return

  const pdfUrl = manualPdfUrl.value.trim()
  if (!pdfUrl) {
    const confirmed = window.confirm('Clear the current PDF URL for this paper?')
    if (!confirmed) return
  } else if (!/^https?:\/\//i.test(pdfUrl)) {
    errorMessage.value = 'PDF URL must start with http:// or https://'
    successMessage.value = ''
    return
  }

  loadingAction.value = 'manual-pdf-url'
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await updatePaper(id, { pdf_url: pdfUrl || null })
    successMessage.value = pdfUrl ? 'PDF URL saved.' : 'PDF URL cleared.'
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to save PDF URL'
  } finally {
    loadingAction.value = null
  }
}

function resolveSelectedPdf() {
  const id = props.paper?.id
  if (!id) return
  void runAction('resolve', () => resolvePdf(id))
}

function downloadSelectedPdf() {
  const id = props.paper?.id
  if (!id) return
  void runAction('download', () => downloadPdf(id))
}

function parseSelectedPdf() {
  const id = props.paper?.id
  if (!id) return
  void runAction('parse', () => parsePdf(id))
}

function extractSelectedAssets() {
  const id = props.paper?.id
  if (!id) return
  void runAction(
    'extract-assets',
    async () => {
      const result = await extractAssets(id)
      assets.value = await fetchAssets(id)
      return result
    },
    false,
  )
}

function loadSelectedAssets() {
  const id = props.paper?.id
  if (!id) return
  void runAction('assets', () => fetchAssets(id), false)
}

function extractSelectedPaper() {
  const id = props.paper?.id
  if (!id) return
  void runAction('extract', () =>
    extractPaper(id, {
      mode: extractionMode.value,
      user_topic: 'LLM inference systems',
      max_chunks: 8,
    }),
  )
}

function processSelectedPaper() {
  const id = props.paper?.id
  if (!id) return
  void runAction('process', () =>
    processPaper(id, {
      resolve_pdf: true,
      download_pdf: true,
      parse_pdf: true,
      extract: true,
      extract_mode: extractionMode.value,
      user_topic: 'LLM inference systems',
      max_chunks: 8,
    }),
  )
}

function refreshSelectedEnrichment() {
  const id = props.paper?.id
  if (!id) return
  void runAction('refresh-enrichment', () => refreshPaperEnrichment(id))
}

function loadLatestExtraction() {
  const id = props.paper?.id
  if (!id) return
  void runAction('latest', () => fetchLatestExtraction(id), false)
}

function previewSelectedMarkdown() {
  const id = props.paper?.id
  if (!id) return
  markdownPreview.value = ''
  markdownPreviewLoaded.value = false
  void runAction('preview-markdown', () => previewMarkdown(id), false)
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function exportSelectedMarkdown() {
  const id = props.paper?.id
  if (!id) return
  void runAction(
    'export-markdown',
    async () => {
      const file = await exportMarkdown(id)
      saveBlob(file.blob, file.filename)
    },
    false,
  )
}

function exportSelectedBibtex() {
  const id = props.paper?.id
  if (!id) return
  void runAction(
    'export-bibtex',
    async () => {
      const file = await exportBibtex(id)
      saveBlob(file.blob, file.filename)
    },
    false,
  )
}

function saveSelectedWorkspace() {
  const id = props.paper?.id
  if (!id) return
  void runAction('save-workspace', () => saveWorkspace(id), false)
}

function saveSelectedTopics() {
  const id = props.paper?.id
  if (!id) return
  const topicNames = topicInput.value
    .split(',')
    .map((topic) => topic.trim())
    .filter(Boolean)
  void runAction('topics', () => updatePaperTopics(id, topicNames))
}

function assetImageSrc(asset: PaperAsset) {
  if (!asset.local_path) return ''
  const normalized = asset.local_path.replace(/\\/g, '/')
  const match = normalized.match(/(?:^|\/)storage\/assets\/(.+)$/)
  if (!match) return ''
  return `${API_BASE}/static/assets/${match[1].split('/').map(encodeURIComponent).join('/')}`
}

function stepClass(status: string) {
  if (status === 'success') return 'border-green-200 bg-green-50 text-green-800'
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-800'
  return 'border-slate-200 bg-slate-50 text-slate-700'
}

function displayValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') return value.toFixed(4)
  return value
}

function summaryValue(key: string) {
  return extractionData.value?.[key]
}

function formatSummaryValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'No data.'
  if (Array.isArray(value)) {
    return value.length ? value.map((item) => `- ${String(item)}`).join('\n') : 'No data.'
  }
  return String(value)
}
</script>

<template>
  <section class="space-y-4">
    <div v-if="!paper" class="panel-card text-sm text-gray-500">Select a paper to see details.</div>

    <div v-else class="space-y-4">
      <section class="panel-card">
        <h2 class="text-lg font-semibold leading-6 text-gray-950">{{ paper.title }}</h2>
        <div class="mt-2 flex flex-wrap gap-2">
          <span class="badge badge-status">{{ paper.status }}</span>
          <span class="badge badge-rank">{{ displayValue(paper.rank_value || paper.venue_rank) }}</span>
          <span class="badge badge-score">Final {{ displayValue(paper.final_score) }}</span>
        </div>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Metadata</h3>
        <dl class="detail-grid">
          <dt>Year</dt>
          <dd>{{ paper.year || '-' }}</dd>
          <dt>Authors</dt>
          <dd>{{ paper.authors?.length ? paper.authors.join(', ') : '-' }}</dd>
          <dt>Venue</dt>
          <dd>{{ paper.venue || '-' }}</dd>
          <dt>Venue Normalized</dt>
          <dd>{{ displayValue(paper.venue_normalized) }}</dd>
          <dt>DOI</dt>
          <dd class="break-all">
            <span v-if="!paper.doi">-</span>
            <a v-else class="text-link" :href="`https://doi.org/${paper.doi}`" target="_blank" rel="noreferrer">
              {{ paper.doi }}
            </a>
          </dd>
          <dt>Citations</dt>
          <dd>{{ paper.citation_count ?? 0 }}</dd>
          <dt>Status</dt>
          <dd>{{ paper.status }}</dd>
          <dt>PDF URL</dt>
          <dd class="break-all">
            <span v-if="!paper.pdf_url">-</span>
            <a v-else class="text-link" :href="paper.pdf_url" target="_blank" rel="noreferrer">{{ paper.pdf_url }}</a>
          </dd>
          <dt>Local PDF</dt>
          <dd class="break-all">{{ paper.local_pdf_path || '-' }}</dd>
        </dl>

        <div class="mt-3">
          <h4 class="mb-1 text-xs font-medium uppercase tracking-normal text-gray-500">Abstract</h4>
          <p class="max-h-32 overflow-auto whitespace-pre-wrap text-sm leading-6 text-gray-700">
            {{ paper.abstract || 'No abstract.' }}
          </p>
        </div>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Rank & Scores</h3>
        <div class="grid grid-cols-2 gap-2">
          <div class="metric-tile">
            <span>Rank</span>
            <strong>{{ displayValue(paper.rank_value || paper.venue_rank) }}</strong>
          </div>
          <div class="metric-tile">
            <span>Final Score</span>
            <strong>{{ displayValue(paper.final_score) }}</strong>
          </div>
        </div>
        <div v-if="readingPriority" class="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
          <div class="mb-1 text-xs font-semibold uppercase tracking-normal text-gray-500">Reading Priority</div>
          <div class="flex flex-wrap items-center gap-2">
            <span class="badge badge-priority" :class="priorityBadgeClass(readingPriority)">
              {{ readingPriority.label }}
            </span>
            <span class="text-xs leading-5 text-gray-600">{{ readingPriorityMeaning }}</span>
          </div>
          <div class="mt-2 rounded-md border border-gray-200 bg-white px-2.5 py-2 text-xs leading-5 text-gray-600">
            <span class="font-semibold text-gray-700">Reason:</span>
            {{ readingPriority.reason }}
          </div>
        </div>
        <dl class="detail-grid mt-3">
          <dt>Publication</dt>
          <dd>{{ displayValue(paper.publication_status) }}</dd>
          <dt>Venue Type</dt>
          <dd>{{ displayValue(paper.venue_type) }}</dd>
          <dt>Rank Source</dt>
          <dd class="break-all">{{ displayValue(paper.rank_source || paper.venue_rank_source) }}</dd>
        </dl>
        <details class="mt-3 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-700">
          <summary class="cursor-pointer font-medium text-gray-600">Rank note and score details</summary>
          <dl class="detail-grid mt-2">
            <dt>Relevance</dt>
            <dd>{{ displayValue(paper.relevance_score) }}</dd>
            <dt>Authority</dt>
            <dd>{{ displayValue(paper.authority_score) }}</dd>
            <dt>Foundation</dt>
            <dd>{{ displayValue(paper.foundation_score) }}</dd>
            <dt>Implementation</dt>
            <dd>{{ displayValue(paper.implementation_score) }}</dd>
            <dt>Survey Value</dt>
            <dd>{{ displayValue(paper.survey_value_score) }}</dd>
            <dt>Frontier</dt>
            <dd>{{ displayValue(paper.frontier_score) }}</dd>
            <dt>Accessibility</dt>
            <dd>{{ displayValue(paper.accessibility_score) }}</dd>
          </dl>
          <p class="mt-2 leading-5">{{ displayValue(paper.rank_note || paper.venue_rank_note) }}</p>
        </details>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Topics</h3>
        <div class="mb-3 flex flex-wrap gap-2">
          <span v-if="!paper.topics?.length" class="text-sm text-slate-500">No topics assigned.</span>
          <template v-else>
            <span v-for="topic in paper.topics" :key="topic" class="badge badge-status">
              {{ topic }}
            </span>
          </template>
        </div>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">Comma-separated topics</span>
          <input
            v-model="topicInput"
            class="input"
            type="text"
            list="topic-options"
            placeholder="AI Systems / Inference Systems, Systems Optimization"
          />
        </label>
        <datalist id="topic-options">
          <option v-for="topic in topics" :key="topic.id" :value="topic.name" />
        </datalist>
        <button class="button-primary mt-3" type="button" :disabled="!!loadingAction" @click="saveSelectedTopics">
          {{ loadingAction === 'topics' ? 'Saving...' : 'Save Topics' }}
        </button>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Actions</h3>

        <div class="space-y-3">
          <div class="action-group">
            <div class="mb-3">
              <h4>Primary Actions</h4>
              <label class="mode-control mt-2 text-xs font-medium text-slate-500">
                <span>Extraction Mode</span>
                <select v-model="extractionMode" class="mode-select">
                  <option value="openai">openai</option>
                  <option value="mock">mock</option>
                </select>
              </label>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="processSelectedPaper">
                {{ loadingAction === 'process' ? 'Processing...' : 'Process Paper' }}
              </button>
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="saveSelectedWorkspace">
                {{ loadingAction === 'save-workspace' ? 'Saving...' : 'Save to Library' }}
              </button>
            </div>
          </div>

          <div class="action-group">
            <h4>Reading Actions</h4>
            <div class="grid grid-cols-2 gap-2">
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="refreshSelectedEnrichment">
                {{ loadingAction === 'refresh-enrichment' ? 'Refreshing...' : 'Refresh Rank & Score' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="loadLatestExtraction">
                {{ loadingAction === 'latest' ? 'Loading...' : 'Load Summary' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="previewSelectedMarkdown">
                {{ loadingAction === 'preview-markdown' ? 'Loading...' : 'Preview Markdown' }}
              </button>
              <button
                class="button-secondary"
                type="button"
                :disabled="!paper.local_pdf_path"
                @click="showPdfPreview = !showPdfPreview"
              >
                {{ showPdfPreview ? 'Hide PDF' : 'PDF Preview' }}
              </button>
            </div>
          </div>

          <div class="action-group">
            <h4>Export Actions</h4>
            <div class="grid grid-cols-2 gap-2">
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="exportSelectedMarkdown">
                {{ loadingAction === 'export-markdown' ? 'Exporting...' : 'Export Markdown' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="exportSelectedBibtex">
                {{ loadingAction === 'export-bibtex' ? 'Exporting...' : 'Export BibTeX' }}
              </button>
            </div>
          </div>

          <details class="action-group">
            <summary class="cursor-pointer text-xs font-semibold text-gray-600">Advanced Debug</summary>
            <div class="mt-3 grid grid-cols-2 gap-2">
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="resolveSelectedPdf">
                {{ loadingAction === 'resolve' ? 'Resolving...' : 'Resolve PDF' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="downloadSelectedPdf">
                {{ loadingAction === 'download' ? 'Downloading...' : 'Download PDF' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="parseSelectedPdf">
                {{ loadingAction === 'parse' ? 'Parsing...' : 'Parse PDF' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="extractSelectedPaper">
                {{ loadingAction === 'extract' ? 'Extracting...' : 'Run Extraction' }}
              </button>
              <button class="button-secondary col-span-2" type="button" :disabled="!!loadingAction" @click="extractSelectedAssets">
                {{ loadingAction === 'extract-assets' ? 'Extracting...' : 'Extract Assets' }}
              </button>
            </div>
          </details>
        </div>

        <p v-if="errorMessage" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ errorMessage }}
        </p>
        <p v-if="refreshResult" class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {{ refreshResult.message }} Rank {{ refreshResult.rank_value || '-' }}, score {{ displayValue(refreshResult.final_score) }}.
        </p>
        <p v-if="successMessage" class="mt-3 rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-700">
          {{ successMessage }}
        </p>
      </section>

      <section class="panel-card">
        <details>
          <summary class="cursor-pointer text-xs font-semibold text-gray-500">Danger Zone</summary>
          <div class="mt-3 rounded-lg border border-red-100 bg-red-50/40 p-3">
            <label class="flex items-start gap-2 text-xs leading-5 text-gray-600">
              <input v-model="deleteLocalFiles" class="mt-1" type="checkbox" />
              <span>Also delete local files</span>
            </label>
            <p class="mt-2 text-xs leading-5 text-gray-500">
              删除数据库记录后，该论文会从 Library 中消失。如果勾选 Also delete local files，也会删除本地 PDF/assets/workspace。
            </p>
            <button
              class="button-danger mt-3"
              type="button"
              :disabled="!!loadingAction"
              @click="deleteSelectedPaper"
            >
              {{ loadingAction === 'delete-paper' ? 'Deleting...' : 'Delete Paper' }}
            </button>
          </div>
        </details>
      </section>

      <section v-if="processResult" class="panel-card">
        <h3 class="section-title">Process Result</h3>
        <div class="space-y-2">
          <div
            v-for="step in processResult.steps"
            :key="step.name"
            class="rounded-md border px-3 py-2 text-xs"
            :class="stepClass(step.status)"
          >
            <div class="mb-1 flex items-center justify-between gap-3">
              <span class="font-medium">{{ step.name }}</span>
              <span class="uppercase">{{ step.status }}</span>
            </div>
            <p class="leading-5">{{ step.message }}</p>
          </div>
        </div>
      </section>

      <section class="panel-card">
        <h3 class="section-title">LLM Structured Summary</h3>
        <p v-if="!extractionData" class="text-sm text-slate-500">
          No extraction loaded yet. Use Load Summary after processing the paper.
        </p>
        <div v-else class="space-y-2">
          <div v-for="item in summaryItems" :key="item.key" class="summary-block">
            <h4>{{ item.title }}</h4>
            <pre>{{ formatSummaryValue(summaryValue(item.key)) }}</pre>
          </div>
        </div>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Manual PDF URL</h3>
        <dl class="detail-grid mb-3">
          <dt>Current PDF URL</dt>
          <dd class="break-all">
            <span v-if="!paper.pdf_url">-</span>
            <a v-else class="text-link" :href="paper.pdf_url" target="_blank" rel="noreferrer">{{ paper.pdf_url }}</a>
          </dd>
        </dl>
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">PDF URL</span>
          <input
            v-model="manualPdfUrl"
            class="input"
            type="url"
            placeholder="https://arxiv.org/pdf/..."
          />
        </label>
        <p class="mt-2 text-xs leading-5 text-gray-500">
          Use only legal open-access PDF URLs, e.g. arXiv, OpenReview, official proceedings, author homepage, or institutional repository.
        </p>
        <button class="button-secondary mt-3" type="button" :disabled="!!loadingAction" @click="saveManualPdfUrl">
          {{ loadingAction === 'manual-pdf-url' ? 'Saving...' : 'Save PDF URL' }}
        </button>
      </section>

      <section class="panel-card">
        <h3 class="section-title">PDF Preview</h3>
        <p v-if="paper.local_pdf_path && !pdfPreviewSrc" class="mt-2 text-xs text-slate-500">
          Local PDF path: {{ paper.local_pdf_path }}. Preview needs a file under storage/pdfs.
        </p>
        <iframe
          v-if="showPdfPreview && pdfPreviewSrc"
          class="mt-3 h-[520px] w-full rounded-md border border-slate-200"
          :src="pdfPreviewSrc"
          title="PDF preview"
        ></iframe>
        <p v-if="!paper.local_pdf_path && !paper.pdf_url" class="text-sm text-slate-500">
          No PDF available yet.
        </p>
        <a
          v-if="paper.pdf_url"
          class="mt-2 inline-flex text-xs font-medium text-slate-600 hover:text-slate-950"
          :href="paper.pdf_url"
          target="_blank"
          rel="noreferrer"
        >
          Open source PDF URL
        </a>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Assets</h3>
        <div class="mb-3">
          <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="loadSelectedAssets">
            {{ loadingAction === 'assets' ? 'Loading...' : 'Load Assets' }}
          </button>
        </div>

        <dl class="detail-grid">
          <dt>Asset Count</dt>
          <dd>{{ assetResult?.asset_count ?? assets.length }}</dd>
          <dt>Page Images</dt>
          <dd>{{ assetResult?.page_image_count ?? pageImages.length }}</dd>
          <dt>Figure Captions</dt>
          <dd>{{ assetResult?.figure_caption_count ?? figureCaptions.length }}</dd>
          <dt>Table Captions</dt>
          <dd>{{ assetResult?.table_caption_count ?? tableAssets.filter((asset) => asset.asset_type === 'table_caption').length }}</dd>
        </dl>

        <p v-if="!assets.length" class="mt-3 text-sm text-slate-500">
          No assets loaded yet.
        </p>

        <div v-if="shownPageImages.length" class="mt-3">
          <h4 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Page Images</h4>
          <div class="grid grid-cols-3 gap-2">
            <a
              v-for="asset in shownPageImages"
              :key="asset.id"
              class="block overflow-hidden rounded-md border border-slate-200 bg-slate-50"
              :href="assetImageSrc(asset)"
              target="_blank"
              rel="noreferrer"
            >
              <img
                class="h-28 w-full object-cover"
                :src="assetImageSrc(asset)"
                :alt="`Page ${asset.page_number ?? asset.asset_index}`"
              />
              <span class="block px-2 py-1 text-xs text-slate-600">Page {{ asset.page_number ?? '-' }}</span>
            </a>
          </div>
          <p v-if="pageImages.length > shownPageImages.length" class="mt-2 text-xs text-slate-500">
            Showing first {{ shownPageImages.length }} of {{ pageImages.length }} page images.
          </p>
        </div>

        <div v-if="figureCaptions.length" class="mt-3">
          <h4 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Figure Captions</h4>
          <div class="space-y-2">
            <p
              v-for="asset in figureCaptions"
              :key="asset.id"
              class="max-h-28 overflow-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-700"
            >
              Page {{ asset.page_number ?? '-' }}: {{ asset.caption || asset.text_content || '-' }}
            </p>
          </div>
        </div>

        <div v-if="tableAssets.length" class="mt-3">
          <h4 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Tables</h4>
          <div class="space-y-2">
            <div
              v-for="asset in tableAssets"
              :key="asset.id"
              class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700"
            >
              <div class="mb-1 font-medium text-slate-600">
                {{ asset.asset_type }} - Page {{ asset.page_number ?? '-' }}
              </div>
              <pre class="max-h-32 overflow-auto whitespace-pre-wrap leading-5">{{ asset.text_content || asset.caption || '-' }}</pre>
            </div>
          </div>
        </div>
      </section>

      <section v-if="workspaceResult" class="panel-card">
        <h3 class="section-title">Library Workspace</h3>
        <dl class="detail-grid">
          <dt>Workspace</dt>
          <dd class="break-all">{{ workspaceResult.workspace_path }}</dd>
          <dt>Markdown</dt>
          <dd class="break-all">{{ workspaceResult.markdown_path }}</dd>
          <dt>BibTeX</dt>
          <dd class="break-all">{{ workspaceResult.bibtex_path }}</dd>
          <dt>PDF</dt>
          <dd class="break-all">{{ workspaceResult.pdf_path || '-' }}</dd>
          <dt>Metadata</dt>
          <dd class="break-all">{{ workspaceResult.metadata_path }}</dd>
          <dt>Assets</dt>
          <dd class="break-all">{{ workspaceResult.assets_path || '-' }}</dd>
        </dl>
      </section>

      <section class="panel-card">
        <h3 class="section-title">Markdown Preview</h3>
        <p v-if="loadingAction === 'preview-markdown'" class="text-sm text-slate-500">
          Loading Markdown preview...
        </p>
        <p v-else-if="!markdownPreviewLoaded" class="text-sm text-slate-500">
          Click Preview Markdown to load the exported note without downloading it.
        </p>
        <p v-else-if="!markdownPreview" class="text-sm text-slate-500">
          Markdown export returned an empty document.
        </p>
        <pre
          v-else
          class="max-h-96 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700"
        >{{ markdownPreview }}</pre>
      </section>
    </div>
  </section>
</template>

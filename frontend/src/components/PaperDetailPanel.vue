<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  downloadPdf,
  exportBibtex,
  exportMarkdown,
  extractPaper,
  fetchLatestExtraction,
  parsePdf,
  previewMarkdown,
  processPaper,
  resolvePdf,
} from '../api/papers'
import type { Extraction, Paper, ProcessPaperResponse } from '../types'

const API_BASE = 'http://127.0.0.1:8000'

const props = defineProps<{
  paper: Paper | null
}>()

const emit = defineEmits<{
  refresh: []
}>()

const loadingAction = ref<string | null>(null)
const errorMessage = ref('')
const latestExtraction = ref<Extraction | null>(null)
const processResult = ref<ProcessPaperResponse | null>(null)
const showPdfPreview = ref(false)
const markdownPreview = ref('')
const extractionMode = ref<'mock' | 'openai'>('openai')

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

watch(
  () => props.paper?.id,
  () => {
    errorMessage.value = ''
    latestExtraction.value = null
    processResult.value = null
    loadingAction.value = null
    showPdfPreview.value = false
    markdownPreview.value = ''
  },
)

async function runAction(label: string, action: () => Promise<unknown>, shouldRefresh = true) {
  if (!props.paper) return

  loadingAction.value = label
  errorMessage.value = ''
  try {
    const result = await action()
    if (label === 'latest') {
      latestExtraction.value = result as Extraction
    }
    if (label === 'process') {
      processResult.value = result as ProcessPaperResponse
    }
    if (label === 'preview-markdown') {
      markdownPreview.value = result as string
    }
    if (shouldRefresh) emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
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

function loadLatestExtraction() {
  const id = props.paper?.id
  if (!id) return
  void runAction('latest', () => fetchLatestExtraction(id), false)
}

function previewSelectedMarkdown() {
  const id = props.paper?.id
  if (!id) return
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
  <section class="bg-white">
    <div v-if="!paper" class="p-4 text-sm text-slate-500">Select a paper to see details.</div>

    <div v-else class="divide-y divide-slate-200">
      <section class="p-4">
        <h2 class="text-base font-semibold leading-6 text-slate-950">{{ paper.title }}</h2>
      </section>

      <section class="p-4">
        <h3 class="section-title">Metadata</h3>
        <dl class="detail-grid">
          <dt>Year</dt>
          <dd>{{ paper.year || '-' }}</dd>
          <dt>Venue</dt>
          <dd>{{ paper.venue || '-' }}</dd>
          <dt>Venue Normalized</dt>
          <dd>{{ displayValue(paper.venue_normalized) }}</dd>
          <dt>DOI</dt>
          <dd class="break-all">{{ paper.doi || '-' }}</dd>
          <dt>Citations</dt>
          <dd>{{ paper.citation_count ?? 0 }}</dd>
          <dt>Status</dt>
          <dd>{{ paper.status }}</dd>
          <dt>PDF URL</dt>
          <dd class="break-all">{{ paper.pdf_url || '-' }}</dd>
          <dt>Local PDF</dt>
          <dd class="break-all">{{ paper.local_pdf_path || '-' }}</dd>
        </dl>

        <div class="mt-3">
          <h4 class="mb-1 text-xs font-medium uppercase tracking-normal text-slate-500">Abstract</h4>
          <p class="max-h-32 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-700">
            {{ paper.abstract || 'No abstract.' }}
          </p>
        </div>
      </section>

      <section class="p-4">
        <h3 class="section-title">Rank & Scores</h3>
        <dl class="detail-grid">
          <dt>Rank Source</dt>
          <dd class="break-all">{{ displayValue(paper.rank_source || paper.venue_rank_source) }}</dd>
          <dt>Rank Value</dt>
          <dd>{{ displayValue(paper.rank_value || paper.venue_rank) }}</dd>
          <dt>Publication Status</dt>
          <dd>{{ displayValue(paper.publication_status) }}</dd>
          <dt>Venue Type</dt>
          <dd>{{ displayValue(paper.venue_type) }}</dd>
          <dt>Final Score</dt>
          <dd>{{ displayValue(paper.final_score) }}</dd>
          <dt>Relevance</dt>
          <dd>{{ displayValue(paper.relevance_score) }}</dd>
          <dt>Authority</dt>
          <dd>{{ displayValue(paper.authority_score) }}</dd>
          <dt>Frontier</dt>
          <dd>{{ displayValue(paper.frontier_score) }}</dd>
          <dt>Accessibility</dt>
          <dd>{{ displayValue(paper.accessibility_score) }}</dd>
        </dl>
        <details class="mt-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <summary class="cursor-pointer font-medium text-slate-600">Rank note</summary>
          <p class="mt-2 leading-5">{{ displayValue(paper.rank_note || paper.venue_rank_note) }}</p>
        </details>
      </section>

      <section class="p-4">
        <h3 class="section-title">Actions</h3>
        <label class="mb-3 block">
          <span class="mb-1 block text-xs font-medium text-slate-500">Extraction Mode</span>
          <select v-model="extractionMode" class="input h-9">
            <option value="openai">openai</option>
            <option value="mock">mock</option>
          </select>
        </label>

        <div class="space-y-3">
          <div class="action-group">
            <h4>Primary Workflow</h4>
            <button class="button-primary w-full" type="button" :disabled="!!loadingAction" @click="processSelectedPaper">
              {{ loadingAction === 'process' ? 'Processing...' : 'Process Paper' }}
            </button>
          </div>

          <div class="action-group">
            <h4>Manual Steps</h4>
            <div class="grid grid-cols-2 gap-2">
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="resolveSelectedPdf">
                {{ loadingAction === 'resolve' ? 'Resolving...' : 'Resolve PDF' }}
              </button>
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="downloadSelectedPdf">
                {{ loadingAction === 'download' ? 'Downloading...' : 'Download PDF' }}
              </button>
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="parseSelectedPdf">
                {{ loadingAction === 'parse' ? 'Parsing...' : 'Parse PDF' }}
              </button>
              <button class="button-primary" type="button" :disabled="!!loadingAction" @click="extractSelectedPaper">
                {{ loadingAction === 'extract' ? 'Extracting...' : 'Run Extraction' }}
              </button>
            </div>
          </div>

          <div class="action-group">
            <h4>Review & Export</h4>
            <div class="grid grid-cols-2 gap-2">
              <button class="button-secondary col-span-2" type="button" :disabled="!!loadingAction" @click="loadLatestExtraction">
                {{ loadingAction === 'latest' ? 'Loading...' : 'Load Latest Extraction' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="previewSelectedMarkdown">
                {{ loadingAction === 'preview-markdown' ? 'Loading...' : 'Preview Markdown' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="exportSelectedMarkdown">
                {{ loadingAction === 'export-markdown' ? 'Exporting...' : 'Export Markdown' }}
              </button>
              <button class="button-secondary" type="button" :disabled="!!loadingAction" @click="exportSelectedBibtex">
                {{ loadingAction === 'export-bibtex' ? 'Exporting...' : 'Export BibTeX' }}
              </button>
            </div>
          </div>
        </div>

        <p v-if="errorMessage" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {{ errorMessage }}
        </p>
      </section>

      <section v-if="processResult" class="p-4">
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

      <section class="p-4">
        <h3 class="section-title">LLM Structured Summary</h3>
        <p v-if="!extractionData" class="text-sm text-slate-500">
          No extraction loaded yet. Click Load Latest Extraction or Mock Extract.
        </p>
        <div v-else class="space-y-3">
          <div class="summary-block">
            <h4>Research Background</h4>
            <p>{{ formatSummaryValue(summaryValue('research_background')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Research Problem</h4>
            <p>{{ formatSummaryValue(summaryValue('research_problem')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Methodology</h4>
            <p>{{ formatSummaryValue(summaryValue('methodology')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Main Contributions</h4>
            <pre>{{ formatSummaryValue(summaryValue('main_contributions')) }}</pre>
          </div>
          <div class="summary-block">
            <h4>Experiments / Evaluation</h4>
            <p>{{ formatSummaryValue(summaryValue('experiments_or_evaluation')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Main Conclusions</h4>
            <p>{{ formatSummaryValue(summaryValue('main_conclusions')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Limitations</h4>
            <pre>{{ formatSummaryValue(summaryValue('limitations')) }}</pre>
          </div>
          <div class="summary-block">
            <h4>Keywords</h4>
            <pre>{{ formatSummaryValue(summaryValue('keywords')) }}</pre>
          </div>
          <div class="summary-block">
            <h4>Relevance to User Topic</h4>
            <p>{{ formatSummaryValue(summaryValue('relevance_to_user_topic')) }}</p>
          </div>
          <div class="summary-block">
            <h4>Possible Follow-up Questions</h4>
            <pre>{{ formatSummaryValue(summaryValue('possible_followup_questions')) }}</pre>
          </div>
          <div class="summary-block">
            <h4>Evidence Chunk Indices</h4>
            <pre>{{ formatSummaryValue(summaryValue('evidence_chunk_indices')) }}</pre>
          </div>
        </div>
      </section>

      <section class="p-4">
        <h3 class="section-title">PDF Preview</h3>
        <div class="flex flex-wrap gap-2">
          <button
            v-if="paper.local_pdf_path"
            class="button-secondary"
            type="button"
            @click="showPdfPreview = !showPdfPreview"
          >
            {{ showPdfPreview ? 'Hide PDF Preview' : 'Preview PDF' }}
          </button>
          <a
            v-if="paper.pdf_url"
            class="button-secondary"
            :href="paper.pdf_url"
            target="_blank"
            rel="noreferrer"
          >
            Open PDF URL
          </a>
        </div>

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
      </section>

      <section class="p-4">
        <h3 class="section-title">Markdown Preview</h3>
        <p v-if="!markdownPreview" class="text-sm text-slate-500">
          Click Preview Markdown to load the exported note without downloading it.
        </p>
        <pre
          v-else
          class="max-h-96 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700"
        >{{ markdownPreview }}</pre>
      </section>
    </div>
  </section>
</template>

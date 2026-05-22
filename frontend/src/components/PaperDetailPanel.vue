<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  downloadPdf,
  extractPaper,
  fetchLatestExtraction,
  parsePdf,
  processPaper,
  resolvePdf,
} from '../api/papers'
import type { Extraction, Paper, ProcessPaperResponse } from '../types'

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

watch(
  () => props.paper?.id,
  () => {
    errorMessage.value = ''
    latestExtraction.value = null
    processResult.value = null
    loadingAction.value = null
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
    if (shouldRefresh) emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loadingAction.value = null
  }
}

function extractionPreview(extraction: Extraction) {
  try {
    return JSON.stringify(JSON.parse(extraction.extracted_json), null, 2)
  } catch {
    return extraction.extracted_json
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
      mode: 'mock',
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
      extract_mode: 'mock',
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

function stepClass(status: string) {
  if (status === 'success') return 'border-green-200 bg-green-50 text-green-800'
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-800'
  return 'border-slate-200 bg-slate-50 text-slate-700'
}
</script>

<template>
  <section class="border-b border-slate-200 bg-white p-4">
    <div v-if="!paper" class="text-sm text-slate-500">Select a paper to see details.</div>

    <div v-else>
      <h2 class="mb-3 text-base font-semibold leading-6 text-slate-950">{{ paper.title }}</h2>

      <dl class="grid grid-cols-[112px_1fr] gap-x-3 gap-y-1 text-xs">
        <dt class="text-slate-500">DOI</dt>
        <dd class="break-all text-slate-800">{{ paper.doi || '-' }}</dd>
        <dt class="text-slate-500">Year</dt>
        <dd class="text-slate-800">{{ paper.year || '-' }}</dd>
        <dt class="text-slate-500">Venue</dt>
        <dd class="text-slate-800">{{ paper.venue || '-' }}</dd>
        <dt class="text-slate-500">Citations</dt>
        <dd class="text-slate-800">{{ paper.citation_count ?? 0 }}</dd>
        <dt class="text-slate-500">Status</dt>
        <dd class="text-slate-800">{{ paper.status }}</dd>
        <dt class="text-slate-500">PDF URL</dt>
        <dd class="break-all text-slate-800">{{ paper.pdf_url || '-' }}</dd>
        <dt class="text-slate-500">Local PDF</dt>
        <dd class="break-all text-slate-800">{{ paper.local_pdf_path || '-' }}</dd>
      </dl>

      <div class="mt-4">
        <h3 class="mb-1 text-xs font-medium uppercase tracking-normal text-slate-500">Abstract</h3>
        <p class="max-h-36 overflow-auto whitespace-pre-wrap text-sm leading-6 text-slate-700">
          {{ paper.abstract || 'No abstract.' }}
        </p>
      </div>

      <div class="mt-4 grid grid-cols-2 gap-2">
        <button class="button-primary col-span-2" type="button" :disabled="!!loadingAction" @click="processSelectedPaper">
          {{ loadingAction === 'process' ? 'Processing...' : 'Process Paper' }}
        </button>
        <button class="button-primary" type="button" :disabled="!!loadingAction" @click="resolveSelectedPdf">
          {{ loadingAction === 'resolve' ? 'Resolving...' : 'Resolve PDF' }}
        </button>
        <button class="button-primary" type="button" :disabled="!!loadingAction" @click="downloadSelectedPdf">
          {{ loadingAction === 'download' ? 'Downloading...' : 'Download PDF' }}
        </button>
        <button class="button-primary" type="button" :disabled="!!loadingAction" @click="parseSelectedPdf">
          {{ loadingAction === 'parse' ? 'Parsing...' : 'Parse PDF' }}
        </button>
        <button
          class="button-primary"
          type="button"
          :disabled="!!loadingAction"
          @click="extractSelectedPaper"
        >
          {{ loadingAction === 'extract' ? 'Extracting...' : 'Mock Extract' }}
        </button>
        <button class="button-secondary col-span-2" type="button" :disabled="!!loadingAction" @click="loadLatestExtraction">
          {{ loadingAction === 'latest' ? 'Loading...' : 'Load Latest Extraction' }}
        </button>
      </div>

      <p v-if="errorMessage" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ errorMessage }}
      </p>

      <div v-if="processResult" class="mt-4">
        <h3 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Process Result</h3>
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
      </div>

      <div v-if="latestExtraction" class="mt-4">
        <h3 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Latest Extraction</h3>
        <pre class="max-h-72 overflow-auto rounded-md border border-slate-200 bg-slate-50 p-3 text-xs leading-5 text-slate-700">{{ extractionPreview(latestExtraction) }}</pre>
      </div>
    </div>
  </section>
</template>

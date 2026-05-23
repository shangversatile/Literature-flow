<script setup lang="ts">
import { ref } from 'vue'
import { processBatch } from '../api/papers'
import type { BatchProcessResponse } from '../types'

const props = defineProps<{
  selectedPaperIds: number[]
}>()

const emit = defineEmits<{
  refresh: []
}>()

const resolvePdf = ref(true)
const downloadPdf = ref(true)
const parsePdf = ref(true)
const extract = ref(true)
const extractAssets = ref(false)
const saveWorkspace = ref(false)
const extractMode = ref<'mock' | 'openai'>('openai')
const maxChunks = ref(8)
const loading = ref(false)
const errorMessage = ref('')
const result = ref<BatchProcessResponse | null>(null)
const resultVisible = ref(true)
const resultOpen = ref(true)

async function runBatch() {
  if (!props.selectedPaperIds.length) return
  if (props.selectedPaperIds.length > 20) {
    errorMessage.value = 'Select at most 20 papers for one batch.'
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    result.value = await processBatch({
      paper_ids: props.selectedPaperIds,
      resolve_pdf: resolvePdf.value,
      download_pdf: downloadPdf.value,
      parse_pdf: parsePdf.value,
      extract: extract.value,
      extract_assets: extractAssets.value,
      save_workspace: saveWorkspace.value,
      extract_mode: extractMode.value,
      user_topic: 'LLM inference systems',
      max_chunks: maxChunks.value,
    })
    resultVisible.value = true
    resultOpen.value = true
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Batch process failed'
  } finally {
    loading.value = false
  }
}

function clearResults() {
  result.value = null
  errorMessage.value = ''
  resultVisible.value = false
  resultOpen.value = false
}

function updateResultOpen(event: Event) {
  resultOpen.value = (event.target as HTMLDetailsElement).open
}

function stepClass(status: string) {
  if (status === 'success') return 'border-green-200 bg-green-50 text-green-800'
  if (status === 'failed') return 'border-red-200 bg-red-50 text-red-800'
  return 'border-slate-200 bg-slate-50 text-slate-700'
}
</script>

<template>
  <section class="batch-panel">
    <p v-if="selectedPaperIds.length === 0" class="text-sm text-gray-500">
      Select papers from the table to batch process.
    </p>

    <template v-else>
      <div class="flex flex-wrap items-center gap-3">
        <div class="text-sm font-semibold text-gray-900">Selected: {{ selectedPaperIds.length }}</div>
        <label class="mode-control text-xs text-gray-600">
          <span>Mode</span>
          <select v-model="extractMode" class="mode-select text-xs">
            <option value="openai">openai</option>
            <option value="mock">mock</option>
          </select>
        </label>
        <button
          class="button-primary"
          type="button"
          :disabled="loading || selectedPaperIds.length === 0 || selectedPaperIds.length > 20"
          @click="runBatch"
        >
          {{ loading ? 'Processing...' : 'Batch Process Selected' }}
        </button>
        <span class="text-xs text-gray-500">Max 20 papers. OpenAI mode may use API quota.</span>
      </div>

      <details class="mt-2 text-xs text-gray-700">
        <summary class="cursor-pointer font-medium text-gray-600">Batch options</summary>
        <div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
          <label class="flex items-center gap-1.5">
            <input v-model="resolvePdf" type="checkbox" />
            resolve_pdf
          </label>
          <label class="flex items-center gap-1.5">
            <input v-model="downloadPdf" type="checkbox" />
            download_pdf
          </label>
          <label class="flex items-center gap-1.5">
            <input v-model="parsePdf" type="checkbox" />
            parse_pdf
          </label>
          <label class="flex items-center gap-1.5">
            <input v-model="extract" type="checkbox" />
            extract
          </label>
          <label class="flex items-center gap-1.5">
            <input v-model="extractAssets" type="checkbox" />
            extract_assets
          </label>
          <label class="flex items-center gap-1.5">
            <input v-model="saveWorkspace" type="checkbox" />
            save_workspace
          </label>
          <label class="flex items-center gap-1.5">
            <span>max_chunks</span>
            <input v-model.number="maxChunks" class="input h-8 w-20 py-1 text-xs" max="20" min="1" type="number" />
          </label>
        </div>
      </details>
    </template>

    <p v-if="errorMessage" class="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div v-if="result" class="batch-result-panel">
      <div class="batch-result-actions">
        <button class="button-ghost" type="button" @click="resultVisible = !resultVisible">
          {{ resultVisible ? 'Hide Results' : 'Show Results' }}
        </button>
        <button class="button-ghost" type="button" @click="clearResults">Clear Results</button>
      </div>

      <details v-if="resultVisible" :open="resultOpen" @toggle="updateResultOpen">
        <summary class="cursor-pointer text-xs font-semibold text-gray-700">
          Batch result: total {{ result.total }}, succeeded {{ result.succeeded }}, failed {{ result.failed }}
        </summary>
        <p class="mt-1 text-xs text-gray-500">Results below are from the last batch run.</p>
        <p class="text-xs text-gray-500">Batch results are independent of the currently selected paper.</p>

        <div class="mt-2 flex flex-wrap gap-2">
          <span class="badge badge-muted">total {{ result.total }}</span>
          <span class="badge badge-score">succeeded {{ result.succeeded }}</span>
          <span class="badge badge-muted">skipped {{ result.skipped }}</span>
          <span class="badge badge-warning">failed {{ result.failed }}</span>
        </div>

        <div class="mt-2 max-h-56 space-y-2 overflow-y-auto pr-1">
          <article v-for="paper in result.results" :key="paper.paper_id" class="rounded-md border border-gray-200 bg-white p-2">
            <div class="mb-1 flex flex-wrap items-center justify-between gap-2">
              <div class="min-w-0">
                <h3 class="truncate font-semibold text-gray-900">{{ paper.title || 'Paper not found' }}</h3>
                <p class="text-gray-500">paper {{ paper.paper_id }} / {{ paper.status }} / {{ paper.final_status || '-' }}</p>
              </div>
              <span v-if="paper.error" class="text-red-700">{{ paper.error }}</span>
            </div>
            <div class="grid gap-1 md:grid-cols-2 xl:grid-cols-3">
              <div
                v-for="step in paper.steps"
                :key="`${paper.paper_id}-${step.name}`"
                class="rounded border px-2 py-1"
                :class="stepClass(step.status)"
              >
                <div class="flex justify-between gap-2 font-medium">
                  <span>{{ step.name }}</span>
                  <span>{{ step.status }}</span>
                </div>
                <p class="mt-0.5 leading-4">{{ step.message }}</p>
              </div>
            </div>
          </article>
        </div>
      </details>
    </div>
  </section>
</template>

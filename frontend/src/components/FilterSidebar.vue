<script setup lang="ts">
import { reactive, watch } from 'vue'

const stages = [
  { value: 'ALL', label: 'All' },
  { value: 'DISCOVERED', label: 'Discovered' },
  { value: 'PDF_RESOLVED', label: 'PDF Resolved' },
  { value: 'PDF_DOWNLOADED', label: 'PDF Downloaded' },
  { value: 'TEXT_EXTRACTED', label: 'Text Extracted' },
  { value: 'LLM_EXTRACTED', label: 'LLM Extracted' },
]

const capabilities = [
  { value: 'ALL', label: 'All' },
  { value: 'HAS_PDF', label: 'Has PDF' },
  { value: 'HAS_TEXT', label: 'Has Text' },
  { value: 'HAS_EXTRACTION', label: 'Has Extraction' },
]

const emit = defineEmits<{
  'filter-change': [filters: { stage: string; capability: string; year: string }]
  refresh: []
}>()

defineProps<{
  totalPapers: number
  llmExtractedCount: number
  pdfDownloadedCount: number
}>()

const filters = reactive({
  stage: 'ALL',
  capability: 'ALL',
  year: '',
})

watch(
  filters,
  () =>
    emit('filter-change', {
      stage: filters.stage,
      capability: filters.capability,
      year: filters.year,
    }),
  { deep: true },
)
</script>

<template>
  <aside class="workspace-card flex h-full shrink-0 flex-col p-3">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-normal text-gray-500">Library Filters</h2>
      <button class="button-secondary" type="button" @click="emit('refresh')">Refresh</button>
    </div>

    <section class="mb-5 grid grid-cols-1 gap-2 text-xs">
      <div class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
        <div class="text-gray-500">Total Papers</div>
        <div class="mt-1 text-base font-semibold text-gray-950">{{ totalPapers }}</div>
      </div>
      <div class="grid grid-cols-2 gap-2">
        <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
          <div class="text-gray-500">LLM Ready</div>
          <div class="mt-1 font-semibold text-gray-950">{{ llmExtractedCount }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
          <div class="text-gray-500">PDFs</div>
          <div class="mt-1 font-semibold text-gray-950">{{ pdfDownloadedCount }}</div>
        </div>
      </div>
    </section>

    <section class="mb-5">
      <h2 class="mb-2 text-xs font-medium uppercase tracking-normal text-gray-500">Current Stage</h2>
      <div class="space-y-1">
        <button
          v-for="stage in stages"
          :key="stage.value"
          type="button"
          class="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50"
          :class="{ 'bg-gray-950 font-semibold text-white hover:bg-gray-950': filters.stage === stage.value }"
          @click="filters.stage = stage.value"
        >
          {{ stage.label }}
        </button>
      </div>
    </section>

    <section class="mb-5">
      <h2 class="mb-2 text-xs font-medium uppercase tracking-normal text-gray-500">Capabilities</h2>
      <div class="space-y-1">
        <button
          v-for="capability in capabilities"
          :key="capability.value"
          type="button"
          class="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50"
          :class="{ 'bg-gray-950 font-semibold text-white hover:bg-gray-950': filters.capability === capability.value }"
          @click="filters.capability = capability.value"
        >
          {{ capability.label }}
        </button>
      </div>
    </section>

    <section>
      <label class="mb-2 block text-xs font-medium uppercase tracking-normal text-gray-500" for="year-filter">
        Year
      </label>
      <input
        id="year-filter"
        v-model="filters.year"
        class="input"
        inputmode="numeric"
        placeholder="e.g. 2024"
        type="text"
      />
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchPapers } from './api/papers'
import FilterSidebar from './components/FilterSidebar.vue'
import PaperDetailPanel from './components/PaperDetailPanel.vue'
import PaperTable from './components/PaperTable.vue'
import RagAskBox from './components/RagAskBox.vue'
import SearchPanel from './components/SearchPanel.vue'
import type { Paper } from './types'

const papers = ref<Paper[]>([])
const selectedPaperId = ref<number | null>(null)
const stageFilter = ref('ALL')
const capabilityFilter = ref('ALL')
const yearFilter = ref('')
const loading = ref(false)
const errorMessage = ref('')

const selectedPaper = computed(() => {
  return papers.value.find((paper) => paper.id === selectedPaperId.value) ?? null
})

const filteredPapers = computed(() => {
  const year = yearFilter.value.trim()

  return papers.value.filter((paper) => {
    const stageMatches = stageFilter.value === 'ALL' || paper.status === stageFilter.value
    const capabilityMatches = capabilityFilter.value === 'ALL' || paperMatchesCapability(paper, capabilityFilter.value)
    const yearMatches = !year || String(paper.year ?? '').includes(year)
    return stageMatches && capabilityMatches && yearMatches
  })
})

const llmExtractedCount = computed(() => {
  return papers.value.filter((paper) => paper.status === 'LLM_EXTRACTED').length
})

const pdfDownloadedCount = computed(() => {
  return papers.value.filter((paper) => paper.status === 'PDF_DOWNLOADED' || paper.local_pdf_path).length
})

async function loadPapers() {
  loading.value = true
  errorMessage.value = ''
  try {
    papers.value = await fetchPapers()
    if (
      selectedPaperId.value &&
      !papers.value.some((paper) => paper.id === selectedPaperId.value)
    ) {
      selectedPaperId.value = null
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load papers'
  } finally {
    loading.value = false
  }
}

function paperMatchesCapability(paper: Paper, capability: string) {
  if (capability === 'HAS_PDF') {
    return (
      Boolean(paper.local_pdf_path) ||
      ['PDF_DOWNLOADED', 'TEXT_EXTRACTED', 'LLM_EXTRACTED'].includes(paper.status)
    )
  }
  if (capability === 'HAS_TEXT') {
    return ['TEXT_EXTRACTED', 'LLM_EXTRACTED'].includes(paper.status)
  }
  if (capability === 'HAS_EXTRACTION') {
    return paper.status === 'LLM_EXTRACTED'
  }
  return true
}

function handleFilterChange(filters: { stage: string; capability: string; year: string }) {
  stageFilter.value = filters.stage
  capabilityFilter.value = filters.capability
  yearFilter.value = filters.year
}

function selectPaper(paper: Paper) {
  selectedPaperId.value = paper.id
}

onMounted(loadPapers)
</script>

<template>
  <main class="app-shell flex h-screen flex-col overflow-hidden">
    <header class="shrink-0 border-b border-gray-200 bg-white px-6 py-4">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-lg font-semibold tracking-tight text-gray-950">LitFlow</h1>
          <p class="text-xs text-gray-500">Automated Literature Intelligence Workspace</p>
        </div>
        <div class="text-right text-xs leading-5 text-gray-500">
          <div>Backend: 127.0.0.1:8000</div>
          <div>Frontend: localhost:5173</div>
          <div>
            <span v-if="loading">Refreshing library...</span>
            <span v-else-if="errorMessage" class="text-red-600">{{ errorMessage }}</span>
            <span v-else>{{ filteredPapers.length }} visible / {{ papers.length }} total</span>
          </div>
        </div>
      </div>
    </header>

    <div class="shrink-0 px-4 pt-4">
      <SearchPanel @refresh="loadPapers" />
    </div>

    <div class="grid min-h-0 flex-1 grid-cols-[230px_minmax(560px,1fr)_470px] gap-4 overflow-hidden p-4">
      <FilterSidebar
        :total-papers="papers.length"
        :llm-extracted-count="llmExtractedCount"
        :pdf-downloaded-count="pdfDownloadedCount"
        @filter-change="handleFilterChange"
        @refresh="loadPapers"
      />

      <section class="workspace-card flex min-w-0 flex-col overflow-hidden">
        <div v-if="!loading && papers.length === 0" class="flex flex-1 items-center justify-center p-6 text-sm text-gray-500">
          Search and save papers to build your library.
        </div>

        <PaperTable
          v-else
          class="min-h-0 flex-1"
          :papers="filteredPapers"
          :selected-paper-id="selectedPaperId"
          @select="selectPaper"
        />
      </section>

      <aside class="flex min-w-0 flex-col gap-4 overflow-auto">
        <PaperDetailPanel :paper="selectedPaper" @refresh="loadPapers" />
        <RagAskBox :paper-id="selectedPaperId" />
      </aside>
    </div>
  </main>
</template>

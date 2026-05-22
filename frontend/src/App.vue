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
const statusFilter = ref('ALL')
const yearFilter = ref('')
const loading = ref(false)
const errorMessage = ref('')

const selectedPaper = computed(() => {
  return papers.value.find((paper) => paper.id === selectedPaperId.value) ?? null
})

const filteredPapers = computed(() => {
  const year = yearFilter.value.trim()

  return papers.value.filter((paper) => {
    const statusMatches = statusFilter.value === 'ALL' || paper.status === statusFilter.value
    const yearMatches = !year || String(paper.year ?? '').includes(year)
    return statusMatches && yearMatches
  })
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

function handleFilterChange(filters: { status: string; year: string }) {
  statusFilter.value = filters.status
  yearFilter.value = filters.year
}

function selectPaper(paper: Paper) {
  selectedPaperId.value = paper.id
}

onMounted(loadPapers)
</script>

<template>
  <main class="flex h-screen flex-col overflow-hidden bg-slate-50 text-slate-900">
    <header class="shrink-0 border-b border-slate-200 bg-white px-5 py-3">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-base font-semibold tracking-tight text-slate-950">LitFlow</h1>
          <p class="text-xs text-slate-500">
            {{ filteredPapers.length }} visible · {{ papers.length }} total
            <span v-if="selectedPaper"> · Reading #{{ selectedPaper.id }}</span>
          </p>
        </div>
        <div class="text-xs text-slate-500">
          <span v-if="loading">Refreshing library...</span>
          <span v-else-if="errorMessage" class="text-red-600">{{ errorMessage }}</span>
          <span v-else>Workspace ready</span>
        </div>
      </div>
    </header>

    <SearchPanel @refresh="loadPapers" />

    <div class="grid min-h-0 flex-1 grid-cols-[220px_minmax(520px,1fr)_440px] overflow-hidden">
      <FilterSidebar @filter-change="handleFilterChange" @refresh="loadPapers" />

      <section class="flex min-w-0 flex-col overflow-hidden border-r border-slate-200 bg-white">
        <div v-if="!loading && papers.length === 0" class="flex flex-1 items-center justify-center p-6 text-sm text-slate-500">
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

      <aside class="flex min-w-0 flex-col overflow-auto bg-white">
        <PaperDetailPanel :paper="selectedPaper" @refresh="loadPapers" />
        <RagAskBox :paper-id="selectedPaperId" />
      </aside>
    </div>
  </main>
</template>

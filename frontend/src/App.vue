<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchPapers, refreshEnrichmentBatch } from './api/papers'
import { fetchTopics, seedDefaultTopics } from './api/topics'
import BatchProcessPanel from './components/BatchProcessPanel.vue'
import FilterSidebar from './components/FilterSidebar.vue'
import LibraryAskBox from './components/LibraryAskBox.vue'
import PaperDetailPanel from './components/PaperDetailPanel.vue'
import PaperTable from './components/PaperTable.vue'
import RagAskBox from './components/RagAskBox.vue'
import SearchCampaignPanel from './components/SearchCampaignPanel.vue'
import SearchPanel from './components/SearchPanel.vue'
import type { Paper, ResearchTopic } from './types'
import { computeReadingPriority } from './utils/paperQuality'

const papers = ref<Paper[]>([])
const topics = ref<ResearchTopic[]>([])
const selectedPaperId = ref<number | null>(null)
const batchMode = ref(false)
const selectedPaperIds = ref<number[]>([])
const activeTool = ref<'search' | 'campaign' | 'ask-library'>('search')
const toolsCollapsed = ref(false)
const stageFilter = ref('ALL')
const capabilityFilter = ref('ALL')
const priorityFilter = ref('ALL')
const yearFilter = ref('')
const topicFilter = ref('ALL')
const loading = ref(false)
const refreshingRankings = ref(false)
const errorMessage = ref('')
const maintenanceMessage = ref('')

const selectedPaper = computed(() => {
  return papers.value.find((paper) => paper.id === selectedPaperId.value) ?? null
})

const filteredPapers = computed(() => {
  const year = yearFilter.value.trim()

  return papers.value.filter((paper) => {
    const stageMatches = stageFilter.value === 'ALL' || paper.status === stageFilter.value
    const capabilityMatches = capabilityFilter.value === 'ALL' || paperMatchesCapability(paper, capabilityFilter.value)
    const priorityMatches =
      priorityFilter.value === 'ALL' || computeReadingPriority(paper).label === priorityFilter.value
    const yearMatches = !year || String(paper.year ?? '').includes(year)
    const topicMatches = topicFilter.value === 'ALL' || (paper.topics || []).includes(topicFilter.value)
    return stageMatches && capabilityMatches && priorityMatches && yearMatches && topicMatches
  })
})

const llmExtractedCount = computed(() => {
  return papers.value.filter((paper) => paper.status === 'LLM_EXTRACTED').length
})

const pdfDownloadedCount = computed(() => {
  return papers.value.filter((paper) => paper.status === 'PDF_DOWNLOADED' || paper.local_pdf_path).length
})

const mustReadCount = computed(() => {
  return papers.value.filter((paper) => computeReadingPriority(paper).label === 'Must Read').length
})

const highPriorityCount = computed(() => {
  return papers.value.filter((paper) => computeReadingPriority(paper).label === 'High Priority').length
})

const frontierWatchCount = computed(() => {
  return papers.value.filter((paper) => computeReadingPriority(paper).label === 'Frontier Watch').length
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
    const existingIds = new Set(papers.value.map((paper) => paper.id))
    selectedPaperIds.value = selectedPaperIds.value.filter((id) => existingIds.has(id))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load papers'
  } finally {
    loading.value = false
  }
}

async function loadTopics() {
  try {
    topics.value = await fetchTopics()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load topics'
  }
}

async function handleSeedDefaultTopics() {
  loading.value = true
  errorMessage.value = ''
  try {
    topics.value = await seedDefaultTopics()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to seed default topics'
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

function handleFilterChange(filters: { stage: string; capability: string; priority: string; year: string; topic: string }) {
  stageFilter.value = filters.stage
  capabilityFilter.value = filters.capability
  priorityFilter.value = filters.priority
  yearFilter.value = filters.year
  topicFilter.value = filters.topic
}

function selectPaper(paper: Paper) {
  selectedPaperId.value = paper.id
}

function updateSelectedPaperIds(paperIds: number[]) {
  selectedPaperIds.value = paperIds
}

function enterBatchMode() {
  batchMode.value = true
}

function exitBatchMode() {
  batchMode.value = false
  selectedPaperIds.value = []
}

function clearBatchSelection() {
  selectedPaperIds.value = []
}

async function refreshLibrary() {
  await Promise.all([loadPapers(), loadTopics()])
}

async function handlePaperDeleted(message?: string) {
  selectedPaperId.value = null
  maintenanceMessage.value = message || 'Paper deleted.'
  await loadPapers()
}

async function refreshAllRankings() {
  refreshingRankings.value = true
  maintenanceMessage.value = ''
  errorMessage.value = ''
  try {
    const result = await refreshEnrichmentBatch()
    maintenanceMessage.value = `Refreshed rankings: ${result.succeeded}/${result.total} succeeded.`
    await loadPapers()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to refresh rankings'
  } finally {
    refreshingRankings.value = false
  }
}

onMounted(refreshLibrary)
</script>

<template>
  <main class="app-shell flex h-screen flex-col overflow-hidden">
    <header class="app-header shrink-0 border-b border-gray-200 bg-white px-6 py-3">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h1 class="text-lg font-semibold tracking-tight text-gray-950">LitFlow</h1>
          <p class="text-xs text-gray-500">Automated Literature Intelligence Workspace</p>
        </div>
        <div class="app-status text-right text-xs leading-5 text-gray-500">
          <div class="app-status-pill">Backend: 127.0.0.1:8000</div>
          <div class="app-status-pill">Frontend: localhost:5173</div>
          <div class="app-status-line">
            <span v-if="loading">Refreshing library...</span>
            <span v-else-if="errorMessage" class="text-red-600">{{ errorMessage }}</span>
            <span v-else>{{ filteredPapers.length }} visible / {{ papers.length }} total</span>
          </div>
        </div>
      </div>
    </header>

    <section class="tool-dock">
      <div class="tool-tabs">
        <button
          class="tool-tab"
          type="button"
          :class="{ 'tool-tab-active': activeTool === 'search' }"
          @click="activeTool = 'search'; toolsCollapsed = false"
        >
          Search
        </button>
        <button
          class="tool-tab"
          type="button"
          :class="{ 'tool-tab-active': activeTool === 'campaign' }"
          @click="activeTool = 'campaign'; toolsCollapsed = false"
        >
          Campaign
        </button>
        <button
          class="tool-tab"
          type="button"
          :class="{ 'tool-tab-active': activeTool === 'ask-library' }"
          @click="activeTool = 'ask-library'; toolsCollapsed = false"
        >
          Ask Library
        </button>
        <button class="button-ghost" type="button" :disabled="refreshingRankings" @click="refreshAllRankings">
          {{ refreshingRankings ? 'Refreshing...' : 'Refresh All Rankings' }}
        </button>
        <button class="button-ghost ml-auto" type="button" @click="toolsCollapsed = !toolsCollapsed">
          {{ toolsCollapsed ? 'Expand Tools' : 'Collapse Tools' }}
        </button>
      </div>
      <p v-if="maintenanceMessage" class="mt-1 text-xs text-green-700">{{ maintenanceMessage }}</p>

      <div v-if="!toolsCollapsed" class="tool-panel">
        <SearchPanel v-if="activeTool === 'search'" @refresh="loadPapers" />
        <SearchCampaignPanel v-else-if="activeTool === 'campaign'" @refresh="loadPapers" />
        <LibraryAskBox v-else :topics="topics" />
      </div>
    </section>

    <div class="main-workspace">
      <FilterSidebar
        :total-papers="papers.length"
        :llm-extracted-count="llmExtractedCount"
        :pdf-downloaded-count="pdfDownloadedCount"
        :must-read-count="mustReadCount"
        :high-priority-count="highPriorityCount"
        :frontier-watch-count="frontierWatchCount"
        :topics="topics"
        @filter-change="handleFilterChange"
        @refresh="refreshLibrary"
        @seed-default-topics="handleSeedDefaultTopics"
      />

      <section class="workspace-card flex min-w-0 flex-col overflow-hidden">
        <div v-if="!loading && papers.length === 0" class="flex flex-1 items-center justify-center p-6 text-sm text-gray-500">
          Search and save papers to build your library.
        </div>

        <template v-else>
          <div class="batch-toolbar">
            <button v-if="!batchMode" class="button-secondary" type="button" @click="enterBatchMode">
              Enter Batch Mode
            </button>
            <template v-else>
              <span class="batch-mode-banner">Batch Mode active</span>
              <span class="text-sm font-medium text-gray-700">Selected: {{ selectedPaperIds.length }}</span>
              <button class="button-ghost" type="button" :disabled="selectedPaperIds.length === 0" @click="clearBatchSelection">
                Clear Selection
              </button>
              <button class="button-secondary" type="button" @click="exitBatchMode">Exit Batch Mode</button>
            </template>
          </div>

          <BatchProcessPanel v-if="batchMode" :selected-paper-ids="selectedPaperIds" @refresh="refreshLibrary" />
          <PaperTable
            class="min-h-0 flex-1"
            :papers="filteredPapers"
            :batch-mode="batchMode"
            :selected-paper-id="selectedPaperId"
            :selected-paper-ids="selectedPaperIds"
            @select="selectPaper"
            @selected-change="updateSelectedPaperIds"
          />
        </template>
      </section>

      <aside class="detail-sidebar flex min-w-0 flex-col gap-4 overflow-auto">
        <PaperDetailPanel :paper="selectedPaper" :topics="topics" @refresh="refreshLibrary" @deleted="handlePaperDeleted" />
        <RagAskBox :paper-id="selectedPaperId" />
      </aside>
    </div>
  </main>
</template>

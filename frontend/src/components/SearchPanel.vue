<script setup lang="ts">
import { computed, ref } from 'vue'
import { saveAll, saveSelectedPapers, searchAll } from '../api/search'
import type { PaperSearchResult, SearchSaveResponse } from '../types'

const emit = defineEmits<{
  refresh: []
}>()

const query = ref('')
const limit = ref(10)
const loading = ref<'search' | 'save-selected' | 'save-all' | null>(null)
const errorMessage = ref('')
const searchResults = ref<PaperSearchResult[]>([])
const selectedKeys = ref<Set<string>>(new Set())
const saveResult = ref<SearchSaveResponse | null>(null)

const selectedCount = computed(() => selectedKeys.value.size)
const hasResults = computed(() => searchResults.value.length > 0)

function normalizeLimit(value: number) {
  if (!Number.isFinite(value)) return 10
  return Math.min(Math.max(Math.trunc(value), 1), 50)
}

function resultKey(paper: PaperSearchResult) {
  return paper.doi || `${paper.title}-${paper.year || ''}-${paper.venue || ''}`
}

function displayScore(score: number | null | undefined) {
  return typeof score === 'number' ? score.toFixed(3) : '-'
}

function displayValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function selectedPapers() {
  return searchResults.value.filter((paper) => selectedKeys.value.has(resultKey(paper)))
}

function selectAll() {
  selectedKeys.value = new Set(searchResults.value.map(resultKey))
}

function clearSelection() {
  selectedKeys.value = new Set()
}

function closeResults(clearMessage = true) {
  searchResults.value = []
  clearSelection()
  if (clearMessage) {
    saveResult.value = null
    errorMessage.value = ''
  }
}

function toggleSelection(paper: PaperSearchResult) {
  const next = new Set(selectedKeys.value)
  const key = resultKey(paper)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  selectedKeys.value = next
}

async function runSearch() {
  const trimmedQuery = query.value.trim()
  saveResult.value = null
  errorMessage.value = ''

  if (!trimmedQuery) {
    errorMessage.value = 'Please enter a keyword.'
    return
  }

  const safeLimit = normalizeLimit(limit.value)
  limit.value = safeLimit
  loading.value = 'search'

  try {
    searchResults.value = await searchAll(trimmedQuery, safeLimit)
    clearSelection()
    saveResult.value = null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Search failed'
  } finally {
    loading.value = null
  }
}

async function saveSelected() {
  const papers = selectedPapers()
  saveResult.value = null
  errorMessage.value = ''

  if (papers.length === 0) {
    errorMessage.value = 'Please select at least one paper.'
    return
  }

  loading.value = 'save-selected'
  try {
    saveResult.value = await saveSelectedPapers(papers, query.value.trim())
    closeResults(false)
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Save selected failed'
  } finally {
    loading.value = null
  }
}

async function saveAllResults() {
  const trimmedQuery = query.value.trim()
  saveResult.value = null
  errorMessage.value = ''

  if (!trimmedQuery) {
    errorMessage.value = 'Please enter a keyword.'
    return
  }

  const safeLimit = normalizeLimit(limit.value)
  limit.value = safeLimit
  loading.value = 'save-all'
  try {
    saveResult.value = await saveAll(trimmedQuery, safeLimit)
    closeResults(false)
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Save all failed'
  } finally {
    loading.value = null
  }
}
</script>

<template>
  <section class="border-b border-slate-200 bg-white px-4 py-3">
    <form class="flex flex-wrap items-end gap-2" @submit.prevent="runSearch">
      <label class="min-w-0 flex-1">
        <span class="mb-1 block text-xs font-medium text-slate-500">Search query</span>
        <input v-model="query" class="input h-9" placeholder="flashattention" type="text" />
      </label>

      <label class="w-24">
        <span class="mb-1 block text-xs font-medium text-slate-500">Limit</span>
        <input v-model.number="limit" class="input h-9" max="50" min="1" type="number" />
      </label>

      <button class="button-primary h-9 px-4" type="submit" :disabled="!!loading">
        {{ loading === 'search' ? 'Searching...' : 'Search' }}
      </button>
      <button class="button-secondary h-9 px-4" type="button" :disabled="!!loading" @click="saveAllResults">
        {{ loading === 'save-all' ? 'Saving...' : 'Save All Results' }}
      </button>
    </form>

    <div class="mt-2 min-h-5 text-xs">
      <p v-if="errorMessage" class="text-red-600">{{ errorMessage }}</p>
      <p v-else-if="saveResult" class="text-green-700">
        Saved "{{ saveResult.query }}": inserted {{ saveResult.inserted_count }}, skipped {{ saveResult.skipped_count }}.
      </p>
      <p v-else-if="hasResults" class="text-slate-500">
        {{ searchResults.length }} results. {{ selectedCount }} selected.
      </p>
    </div>

    <div v-if="hasResults" class="mt-3 max-h-72 overflow-auto rounded-md border border-slate-200">
      <div class="flex items-center gap-2 border-b border-slate-200 bg-slate-50 px-3 py-2">
        <span class="mr-2 text-xs font-medium text-slate-600">Search Results</span>
        <button class="button-secondary" type="button" :disabled="!!loading" @click="selectAll">Select All</button>
        <button class="button-secondary" type="button" :disabled="!!loading" @click="clearSelection">Clear Selection</button>
        <button class="button-secondary" type="button" :disabled="!!loading" @click="closeResults()">Close Results</button>
        <button class="button-primary ml-auto" type="button" :disabled="!!loading" @click="saveSelected">
          {{ loading === 'save-selected' ? 'Saving...' : 'Save Selected' }}
        </button>
      </div>

      <table class="w-full table-fixed border-collapse text-left text-xs">
        <thead class="sticky top-0 bg-slate-50 text-slate-500">
          <tr class="border-b border-slate-200">
            <th class="w-[4%] px-2 py-2"></th>
            <th class="w-[35%] px-2 py-2 font-medium">Title</th>
            <th class="w-[8%] px-2 py-2 font-medium">Year</th>
            <th class="w-[13%] px-2 py-2 font-medium">Venue</th>
            <th class="w-[8%] px-2 py-2 font-medium">Rank</th>
            <th class="w-[8%] px-2 py-2 font-medium">Score</th>
            <th class="w-[8%] px-2 py-2 font-medium">Cites</th>
            <th class="w-[9%] px-2 py-2 font-medium">Pub</th>
            <th class="w-[7%] px-2 py-2 font-medium">Sources</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="paper in searchResults" :key="resultKey(paper)" class="border-b border-slate-100">
            <td class="px-2 py-2 align-top">
              <input
                type="checkbox"
                :checked="selectedKeys.has(resultKey(paper))"
                @change="toggleSelection(paper)"
              />
            </td>
            <td class="px-2 py-2 align-top">
              <div class="line-clamp-2 font-medium text-slate-900">{{ paper.title }}</div>
              <div v-if="paper.doi" class="truncate text-slate-400">{{ paper.doi }}</div>
            </td>
            <td class="px-2 py-2 align-top text-slate-600">{{ paper.year || '-' }}</td>
            <td class="truncate px-2 py-2 align-top text-slate-600">
              {{ paper.venue_normalized || paper.venue || '-' }}
            </td>
            <td class="px-2 py-2 align-top text-slate-600">{{ displayValue(paper.rank_value || paper.venue_rank) }}</td>
            <td class="px-2 py-2 align-top text-slate-600">{{ displayScore(paper.final_score) }}</td>
            <td class="px-2 py-2 align-top text-slate-600">{{ paper.citation_count ?? 0 }}</td>
            <td class="px-2 py-2 align-top text-slate-600">{{ displayValue(paper.publication_status) }}</td>
            <td class="truncate px-2 py-2 align-top text-slate-600">{{ paper.sources.join(', ') || paper.source }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

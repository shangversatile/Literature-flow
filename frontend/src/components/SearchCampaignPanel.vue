<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { fetchSearchCampaigns, runSearchCampaign, saveSelectedPapers } from '../api/search'
import type { PaperSearchResult, RunCampaignResponse, SearchCampaign, SearchSaveResponse } from '../types'

const emit = defineEmits<{
  refresh: []
}>()

const campaigns = ref<SearchCampaign[]>([])
const selectedCampaignName = ref('')
const limitPerQuery = ref(8)
const loading = ref<'load' | 'run' | 'save-selected' | null>(null)
const errorMessage = ref('')
const response = ref<RunCampaignResponse | null>(null)
const selectedKeys = ref<Set<string>>(new Set())
const saveResult = ref<SearchSaveResponse | null>(null)

const selectedCampaign = computed(() => {
  return campaigns.value.find((campaign) => campaign.name === selectedCampaignName.value) ?? null
})

const results = computed(() => response.value?.results ?? [])
const selectedCount = computed(() => selectedKeys.value.size)

function normalizeLimit(value: number) {
  if (!Number.isFinite(value)) return 8
  return Math.min(Math.max(Math.trunc(value), 1), 20)
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

function publicationBadgeClass(status: string | null | undefined) {
  if (!status) return 'badge-muted'
  return status.toLowerCase() === 'unpublished' ? 'badge-warning' : 'badge-muted'
}

function clearSelection() {
  selectedKeys.value = new Set()
}

function selectAll() {
  selectedKeys.value = new Set(results.value.map(resultKey))
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

function selectedPapers() {
  return results.value.filter((paper) => selectedKeys.value.has(resultKey(paper)))
}

async function loadCampaigns() {
  loading.value = 'load'
  errorMessage.value = ''
  try {
    campaigns.value = await fetchSearchCampaigns()
    if (!selectedCampaignName.value && campaigns.value.length) {
      selectedCampaignName.value = campaigns.value[0].name
      limitPerQuery.value = campaigns.value[0].default_limit_per_query
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Failed to load campaigns'
  } finally {
    loading.value = null
  }
}

async function runCampaign() {
  const campaign = selectedCampaign.value
  if (!campaign) return

  limitPerQuery.value = normalizeLimit(limitPerQuery.value)
  loading.value = 'run'
  errorMessage.value = ''
  saveResult.value = null
  try {
    response.value = await runSearchCampaign({
      campaign_name: campaign.name,
      limit_per_query: limitPerQuery.value,
      save: false,
    })
    clearSelection()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Campaign search failed'
  } finally {
    loading.value = null
  }
}

async function saveSelected() {
  const papers = selectedPapers()
  if (!papers.length) {
    errorMessage.value = 'Please select at least one paper.'
    return
  }

  loading.value = 'save-selected'
  errorMessage.value = ''
  saveResult.value = null
  try {
    saveResult.value = await saveSelectedPapers(papers, selectedCampaignName.value)
    clearSelection()
    emit('refresh')
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Save selected failed'
  } finally {
    loading.value = null
  }
}

onMounted(loadCampaigns)
</script>

<template>
  <section class="workspace-card px-4 py-3">
    <details>
      <summary class="cursor-pointer text-sm font-semibold text-gray-950">Search Campaign</summary>

      <div class="mt-3 space-y-3">
        <div class="flex flex-wrap items-end gap-3">
          <label class="min-w-[260px] flex-1">
            <span class="mb-1 block text-xs font-semibold text-gray-500">Campaign</span>
            <select v-model="selectedCampaignName" class="input h-10">
              <option v-for="campaign in campaigns" :key="campaign.name" :value="campaign.name">
                {{ campaign.name }}
              </option>
            </select>
          </label>
          <label class="w-36">
            <span class="mb-1 block text-xs font-semibold text-gray-500">Limit / query</span>
            <input v-model.number="limitPerQuery" class="input h-10" max="20" min="1" type="number" />
          </label>
          <button class="button-primary h-10 px-4" type="button" :disabled="!!loading || !selectedCampaign" @click="runCampaign">
            {{ loading === 'run' ? 'Running...' : 'Run Campaign' }}
          </button>
        </div>

        <p v-if="selectedCampaign" class="text-xs leading-5 text-gray-500">
          {{ selectedCampaign.description }} {{ selectedCampaign.queries.length }} curated queries.
        </p>
        <p v-if="errorMessage" class="text-xs text-red-600">{{ errorMessage }}</p>
        <p v-else-if="saveResult" class="text-xs text-green-700">
          Saved "{{ saveResult.query }}": inserted {{ saveResult.inserted_count }}, skipped {{ saveResult.skipped_count }}.
        </p>
        <p v-else-if="response" class="text-xs text-slate-500">
          Raw {{ response.total_raw_results }} / unique {{ response.total_unique_results }}. {{ selectedCount }} selected.
        </p>

        <div v-if="results.length" class="max-h-80 overflow-auto rounded-xl border border-gray-200">
          <div class="sticky top-0 z-20 flex items-center gap-2 border-b border-gray-200 bg-gray-50 px-3 py-2">
            <span class="mr-2 text-xs font-semibold text-gray-700">Campaign Results</span>
            <button class="button-secondary" type="button" :disabled="!!loading" @click="selectAll">Select All</button>
            <button class="button-secondary" type="button" :disabled="!!loading" @click="clearSelection">Clear Selection</button>
            <button class="button-success ml-auto" type="button" :disabled="!!loading" @click="saveSelected">
              {{ loading === 'save-selected' ? 'Saving...' : 'Save Selected' }}
            </button>
          </div>

          <table class="compact-table text-xs">
            <thead>
              <tr>
                <th class="w-[4%] px-2 py-2"></th>
                <th class="w-[39%] px-2 py-2 font-medium">Title</th>
                <th class="w-[8%] px-2 py-2 font-medium">Year</th>
                <th class="w-[17%] px-2 py-2 font-medium">Venue / Rank</th>
                <th class="w-[9%] px-2 py-2 font-medium">Score</th>
                <th class="w-[8%] px-2 py-2 font-medium">Cites</th>
                <th class="w-[8%] px-2 py-2 font-medium">Pub</th>
                <th class="w-[7%] px-2 py-2 font-medium">Sources</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="paper in results" :key="resultKey(paper)" class="border-b border-slate-100">
                <td class="px-2 py-2 align-top">
                  <input
                    type="checkbox"
                    :checked="selectedKeys.has(resultKey(paper))"
                    @change="toggleSelection(paper)"
                  />
                </td>
                <td class="px-2 py-2 align-top">
                  <div class="line-clamp-2 font-semibold text-gray-950">{{ paper.title }}</div>
                  <div v-if="paper.doi" class="truncate text-gray-400">{{ paper.doi }}</div>
                </td>
                <td class="px-2 py-2 align-top text-gray-600">{{ paper.year || '-' }}</td>
                <td class="px-2 py-2 align-top text-gray-600">
                  <div class="truncate">{{ paper.venue_normalized || paper.venue || '-' }}</div>
                  <span class="badge badge-rank mt-1">{{ displayValue(paper.rank_value || paper.venue_rank) }}</span>
                </td>
                <td class="px-2 py-2 align-top"><span class="badge badge-score">{{ displayScore(paper.final_score) }}</span></td>
                <td class="px-2 py-2 align-top text-gray-600">{{ paper.citation_count ?? 0 }}</td>
                <td class="px-2 py-2 align-top">
                  <span class="badge" :class="publicationBadgeClass(paper.publication_status)">
                    {{ displayValue(paper.publication_status) }}
                  </span>
                </td>
                <td class="truncate px-2 py-2 align-top text-gray-600">{{ paper.sources.join(', ') || paper.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </details>
  </section>
</template>

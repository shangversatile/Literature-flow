<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Paper } from '../types'

const props = defineProps<{
  papers: Paper[]
  selectedPaperId: number | null
}>()

const emit = defineEmits<{
  select: [paper: Paper]
}>()

type SortKey = 'year' | 'final_score'

const sortKey = ref<SortKey>('final_score')
const sortDirection = ref<'asc' | 'desc'>('desc')

const sortedPapers = computed(() => {
  return [...props.papers].sort((a, b) => {
    const aValue = a[sortKey.value] ?? -1
    const bValue = b[sortKey.value] ?? -1
    const result = aValue - bValue
    return sortDirection.value === 'asc' ? result : -result
  })
})

function setSort(key: SortKey) {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
    return
  }
  sortKey.value = key
  sortDirection.value = 'desc'
}

function sortMark(key: SortKey) {
  if (sortKey.value !== key) return ''
  return sortDirection.value === 'asc' ? '^' : 'v'
}

function displayScore(score: number | null | undefined) {
  return typeof score === 'number' ? score.toFixed(3) : '-'
}

function displayRank(paper: Paper) {
  return paper.rank_value || paper.venue_rank || '-'
}

function compactRank(paper: Paper) {
  const rank = displayRank(paper)
  return rank.length > 12 ? `${rank.slice(0, 12)}...` : rank
}

function displayStatus(status: string) {
  const labels: Record<string, string> = {
    DISCOVERED: 'Discovered',
    PDF_RESOLVED: 'PDF Resolved',
    PDF_DOWNLOADED: 'PDF Downloaded',
    TEXT_EXTRACTED: 'Text Extracted',
    LLM_EXTRACTED: 'LLM Extracted',
  }
  return labels[status] || status.replace(/_/g, ' ')
}

function displayAuthors(paper: Paper) {
  const authors = paper.authors || []
  if (!authors.length) return '-'
  if (authors.length <= 2) return authors.join(', ')
  return `${authors.slice(0, 2).join(', ')} et al.`
}

function priorityLabel(paper: Paper) {
  if ((paper.final_score ?? 0) >= 0.8) return 'Must Read'
  if ((paper.final_score ?? 0) >= 0.65) return 'High Priority'
  if ((paper.frontier_score ?? 0) >= 0.5 && paper.publication_status?.toLowerCase() === 'unpublished') {
    return 'Frontier Watch'
  }
  return 'Skim'
}

function priorityClass(paper: Paper) {
  const label = priorityLabel(paper)
  if (label === 'Must Read') return 'badge-score'
  if (label === 'High Priority') return 'badge-rank'
  if (label === 'Frontier Watch') return 'badge-warning'
  return 'badge-muted'
}
</script>

<template>
  <div class="paper-table-wrapper h-full bg-white">
    <table class="compact-table">
      <thead>
        <tr>
          <th class="w-[28%] px-3 py-2 font-medium">Title</th>
          <th class="w-[14%] px-3 py-2 font-medium">Authors</th>
          <th class="w-[8%] px-3 py-2 font-medium">
            <button class="table-sort-button" type="button" @click="setSort('year')">
              Year {{ sortMark('year') }}
            </button>
          </th>
          <th class="w-[14%] px-3 py-2 font-medium">Venue</th>
          <th class="rank-cell w-[10%] px-3 py-2 font-medium">Rank</th>
          <th class="score-cell w-[9%] px-3 py-2 font-medium">
            <button class="table-sort-button" type="button" @click="setSort('final_score')">
              Final {{ sortMark('final_score') }}
            </button>
          </th>
          <th class="priority-cell w-[12%] px-3 py-2 font-medium">Priority</th>
          <th class="status-cell w-[13%] px-3 py-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="paper in sortedPapers"
          :key="paper.id"
          class="cursor-pointer"
          :class="{ 'bg-blue-50 hover:bg-blue-50': paper.id === selectedPaperId }"
          @click="emit('select', paper)"
        >
          <td class="px-3 py-2 align-top">
            <div class="line-clamp-2 font-semibold leading-5 text-gray-950" :title="paper.title">{{ paper.title }}</div>
            <div v-if="paper.doi" class="truncate text-xs text-gray-400">{{ paper.doi }}</div>
          </td>
          <td class="truncate px-3 py-2 align-top text-xs text-gray-500">{{ displayAuthors(paper) }}</td>
          <td class="px-3 py-2 align-top text-gray-600">{{ paper.year || '-' }}</td>
          <td class="truncate px-3 py-2 align-top text-gray-600">{{ paper.venue || '-' }}</td>
          <td class="rank-cell px-3 py-2 align-top">
            <span class="badge badge-rank" :title="displayRank(paper)">{{ compactRank(paper) }}</span>
          </td>
          <td class="score-cell px-3 py-2 align-top">
            <span class="badge badge-score">{{ displayScore(paper.final_score) }}</span>
          </td>
          <td class="priority-cell px-3 py-2 align-top">
            <span class="badge badge-priority" :class="priorityClass(paper)">{{ priorityLabel(paper) }}</span>
          </td>
          <td class="status-cell px-3 py-2 align-top">
            <span class="badge badge-status">
              {{ displayStatus(paper.status) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

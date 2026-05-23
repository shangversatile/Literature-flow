<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Paper } from '../types'
import { computeReadingPriority, priorityBadgeClass } from '../utils/paperQuality'

const props = defineProps<{
  papers: Paper[]
  batchMode: boolean
  selectedPaperId: number | null
  selectedPaperIds: number[]
}>()

const emit = defineEmits<{
  select: [paper: Paper]
  'selected-change': [paperIds: number[]]
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

const selectedVisibleCount = computed(() => {
  const visibleIds = new Set(sortedPapers.value.map((paper) => paper.id))
  return props.selectedPaperIds.filter((id) => visibleIds.has(id)).length
})

const allVisibleSelected = computed(() => {
  return sortedPapers.value.length > 0 && selectedVisibleCount.value === sortedPapers.value.length
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

function isSelected(paperId: number) {
  return props.selectedPaperIds.includes(paperId)
}

function togglePaper(paperId: number) {
  if (isSelected(paperId)) {
    emit(
      'selected-change',
      props.selectedPaperIds.filter((id) => id !== paperId),
    )
    return
  }
  emit('selected-change', [...props.selectedPaperIds, paperId])
}

function toggleAllVisible() {
  const visibleIds = sortedPapers.value.map((paper) => paper.id)
  if (allVisibleSelected.value) {
    const visibleSet = new Set(visibleIds)
    emit(
      'selected-change',
      props.selectedPaperIds.filter((id) => !visibleSet.has(id)),
    )
    return
  }
  emit('selected-change', Array.from(new Set([...props.selectedPaperIds, ...visibleIds])))
}

</script>

<template>
  <div class="paper-table-wrapper h-full min-w-0 max-w-full bg-white">
    <table class="compact-table">
      <thead>
        <tr>
          <th v-if="batchMode" class="w-10 px-3 py-2 font-medium">
            <input
              type="checkbox"
              :checked="allVisibleSelected"
              :disabled="sortedPapers.length === 0"
              @click.stop
              @change="toggleAllVisible"
            />
          </th>
          <th class="title-cell px-3 py-2 font-medium">Title</th>
          <th class="authors-cell px-3 py-2 font-medium">Authors</th>
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
          :class="{
            'bg-slate-50': batchMode && isSelected(paper.id) && paper.id !== selectedPaperId,
            'bg-blue-50 hover:bg-blue-50': paper.id === selectedPaperId,
          }"
          @click="emit('select', paper)"
        >
          <td v-if="batchMode" class="w-10 px-3 py-2 align-top">
            <input
              type="checkbox"
              :checked="isSelected(paper.id)"
              @click.stop
              @change="togglePaper(paper.id)"
            />
          </td>
          <td class="title-cell px-3 py-2 align-top">
            <div class="line-clamp-2 font-semibold leading-5 text-gray-950" :title="paper.title">{{ paper.title }}</div>
            <div v-if="paper.doi" class="truncate text-xs text-gray-400">{{ paper.doi }}</div>
            <div v-if="paper.topics?.length" class="mt-1 flex flex-wrap gap-1">
              <span v-for="topic in paper.topics.slice(0, 2)" :key="topic" class="badge badge-status">
                {{ topic }}
              </span>
            </div>
          </td>
          <td class="authors-cell truncate px-3 py-2 align-top text-xs text-gray-500">{{ displayAuthors(paper) }}</td>
          <td class="px-3 py-2 align-top text-gray-600">{{ paper.year || '-' }}</td>
          <td class="truncate px-3 py-2 align-top text-gray-600">{{ paper.venue || '-' }}</td>
          <td class="rank-cell px-3 py-2 align-top">
            <span class="badge badge-rank" :title="displayRank(paper)">{{ compactRank(paper) }}</span>
          </td>
          <td class="score-cell px-3 py-2 align-top">
            <span class="badge badge-score">{{ displayScore(paper.final_score) }}</span>
          </td>
          <td class="priority-cell px-3 py-2 align-top">
            <span
              class="badge badge-priority"
              :class="priorityBadgeClass(computeReadingPriority(paper))"
              :title="computeReadingPriority(paper).reason"
            >
              {{ computeReadingPriority(paper).label }}
            </span>
          </td>
          <td class="status-cell px-3 py-2 align-top">
            <span class="badge badge-status" :title="displayStatus(paper.status)">
              {{ displayStatus(paper.status) }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

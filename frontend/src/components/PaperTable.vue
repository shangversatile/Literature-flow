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

type SortKey = 'year' | 'citation_count' | 'final_score'

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
</script>

<template>
  <div class="h-full overflow-auto border-x border-slate-200 bg-white">
    <table class="w-full table-fixed border-collapse text-left text-sm">
      <thead class="sticky top-0 z-10 border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
        <tr>
          <th class="w-[32%] px-3 py-2 font-medium">Title</th>
          <th class="w-[9%] px-3 py-2 font-medium">
            <button class="table-sort-button" type="button" @click="setSort('year')">
              Year {{ sortMark('year') }}
            </button>
          </th>
          <th class="w-[14%] px-3 py-2 font-medium">Venue</th>
          <th class="w-[9%] px-3 py-2 font-medium">
            <button class="table-sort-button" type="button" @click="setSort('citation_count')">
              Cites {{ sortMark('citation_count') }}
            </button>
          </th>
          <th class="w-[10%] px-3 py-2 font-medium">
            <button class="table-sort-button" type="button" @click="setSort('final_score')">
              Score {{ sortMark('final_score') }}
            </button>
          </th>
          <th class="w-[9%] px-3 py-2 font-medium">Rank</th>
          <th class="w-[11%] px-3 py-2 font-medium">Pub</th>
          <th class="w-[6%] px-3 py-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="paper in sortedPapers"
          :key="paper.id"
          class="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
          :class="{ 'bg-blue-50 hover:bg-blue-50': paper.id === selectedPaperId }"
          @click="emit('select', paper)"
        >
          <td class="px-3 py-2 align-top">
            <div class="line-clamp-2 font-medium leading-5 text-slate-900">{{ paper.title }}</div>
            <div v-if="paper.doi" class="truncate text-xs text-slate-400">{{ paper.doi }}</div>
          </td>
          <td class="px-3 py-2 align-top text-slate-600">{{ paper.year || '-' }}</td>
          <td class="truncate px-3 py-2 align-top text-slate-600">{{ paper.venue || '-' }}</td>
          <td class="px-3 py-2 align-top text-slate-600">{{ paper.citation_count ?? 0 }}</td>
          <td class="px-3 py-2 align-top text-slate-600">{{ displayScore(paper.final_score) }}</td>
          <td class="px-3 py-2 align-top text-slate-600">{{ paper.venue_rank || '-' }}</td>
          <td class="px-3 py-2 align-top text-slate-600">{{ paper.publication_status || '-' }}</td>
          <td class="px-3 py-2 align-top">
            <span class="rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[11px] text-slate-600">
              {{ paper.status }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

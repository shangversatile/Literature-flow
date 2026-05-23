<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { ResearchTopic } from '../types'
import { getPriorityMeaning } from '../utils/paperQuality'

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

const priorities = [
  { value: 'ALL', label: 'All' },
  { value: 'Must Read', label: 'Must Read' },
  { value: 'High Priority', label: 'High Priority' },
  { value: 'Frontier Watch', label: 'Frontier Watch' },
  { value: 'Skim', label: 'Skim' },
  { value: 'Archive', label: 'Archive' },
]

const priorityGuide = [
  { label: 'Must Read', meaning: getPriorityMeaning('Must Read') },
  { label: 'High Priority', meaning: getPriorityMeaning('High Priority') },
  { label: 'Frontier Watch', meaning: getPriorityMeaning('Frontier Watch') },
  { label: 'Skim', meaning: getPriorityMeaning('Skim') },
  { label: 'Archive', meaning: getPriorityMeaning('Archive') },
]

const emit = defineEmits<{
  'filter-change': [filters: { stage: string; capability: string; priority: string; year: string; topic: string }]
  refresh: []
  'seed-default-topics': []
}>()

defineProps<{
  totalPapers: number
  llmExtractedCount: number
  pdfDownloadedCount: number
  mustReadCount: number
  highPriorityCount: number
  frontierWatchCount: number
  topics: ResearchTopic[]
}>()

const filters = reactive({
  stage: 'ALL',
  capability: 'ALL',
  priority: 'ALL',
  topic: 'ALL',
  year: '',
})

watch(
  filters,
  () =>
    emit('filter-change', {
      stage: filters.stage,
      capability: filters.capability,
      priority: filters.priority,
      topic: filters.topic,
      year: filters.year,
    }),
  { deep: true },
)
</script>

<template>
  <aside class="workspace-card flex h-full min-h-0 shrink-0 flex-col overflow-y-auto pr-1 p-3">
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
          <div class="text-gray-500">Must Read</div>
          <div class="mt-1 font-semibold text-gray-950">{{ mustReadCount }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
          <div class="text-gray-500">High Priority</div>
          <div class="mt-1 font-semibold text-gray-950">{{ highPriorityCount }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
          <div class="text-gray-500">Frontier</div>
          <div class="mt-1 font-semibold text-gray-950">{{ frontierWatchCount }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 bg-white px-3 py-2">
          <div class="text-gray-500">LLM Ready</div>
          <div class="mt-1 font-semibold text-gray-950">{{ llmExtractedCount }}</div>
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

    <section class="mb-5">
      <div class="mb-2 flex items-center justify-between gap-2">
        <h2 class="text-xs font-medium uppercase tracking-normal text-gray-500">Topic</h2>
        <button
          v-if="!topics.length"
          class="button-secondary"
          type="button"
          @click="emit('seed-default-topics')"
        >
          Seed Default Topics
        </button>
      </div>
      <div class="space-y-1">
        <button
          type="button"
          class="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50"
          :class="{ 'bg-gray-950 font-semibold text-white hover:bg-gray-950': filters.topic === 'ALL' }"
          @click="filters.topic = 'ALL'"
        >
          All
        </button>
        <button
          v-for="topic in topics"
          :key="topic.id"
          type="button"
          class="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50"
          :class="{ 'bg-gray-950 font-semibold text-white hover:bg-gray-950': filters.topic === topic.name }"
          @click="filters.topic = topic.name"
        >
          {{ topic.name }}
        </button>
      </div>
    </section>

    <section class="mb-5">
      <h2 class="mb-2 text-xs font-medium uppercase tracking-normal text-gray-500">Priority</h2>
      <div class="space-y-1">
        <button
          v-for="priority in priorities"
          :key="priority.value"
          type="button"
          class="w-full rounded-lg px-2.5 py-1.5 text-left text-xs text-gray-600 hover:bg-gray-50"
          :class="{ 'bg-gray-950 font-semibold text-white hover:bg-gray-950': filters.priority === priority.value }"
          @click="filters.priority = priority.value"
        >
          {{ priority.label }}
        </button>
      </div>
    </section>

    <details class="priority-guide mb-5 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600">
      <summary class="cursor-pointer font-semibold text-gray-700">Reading Priority Guide</summary>
      <div class="mt-3 space-y-2">
        <div v-for="item in priorityGuide" :key="item.label" class="rounded-md bg-gray-50 px-2.5 py-2">
          <div class="font-semibold text-gray-900">{{ item.label }}</div>
          <div class="mt-1 leading-5 text-gray-600">{{ item.meaning }}</div>
        </div>
      </div>
    </details>

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

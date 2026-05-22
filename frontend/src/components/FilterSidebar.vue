<script setup lang="ts">
import { reactive, watch } from 'vue'

const statuses = [
  'ALL',
  'DISCOVERED',
  'PDF_RESOLVED',
  'PDF_DOWNLOADED',
  'TEXT_EXTRACTED',
  'LLM_EXTRACTED',
]

const emit = defineEmits<{
  'filter-change': [filters: { status: string; year: string }]
  refresh: []
}>()

const filters = reactive({
  status: 'ALL',
  year: '',
})

watch(
  filters,
  () => emit('filter-change', { status: filters.status, year: filters.year }),
  { deep: true },
)
</script>

<template>
  <aside class="flex h-full shrink-0 flex-col border-r border-slate-200 bg-slate-50 p-3">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-xs font-semibold uppercase tracking-normal text-slate-500">Library</h2>
      <button class="button-secondary" type="button" @click="emit('refresh')">Refresh</button>
    </div>

    <section class="mb-5">
      <h2 class="mb-2 text-xs font-medium uppercase tracking-normal text-slate-500">Status</h2>
      <div class="space-y-1">
        <button
          v-for="status in statuses"
          :key="status"
          type="button"
          class="w-full rounded-md px-2 py-1.5 text-left text-xs text-slate-700 hover:bg-white"
          :class="{ 'bg-white font-medium text-slate-950 shadow-sm ring-1 ring-slate-200': filters.status === status }"
          @click="filters.status = status"
        >
          {{ status }}
        </button>
      </div>
    </section>

    <section>
      <label class="mb-2 block text-xs font-medium uppercase tracking-normal text-slate-500" for="year-filter">
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

<script setup lang="ts">
import { ref, watch } from 'vue'
import { askPaper } from '../api/papers'
import type { AskResponse } from '../types'

const props = defineProps<{
  paperId: number | null
}>()

const question = ref('')
const topK = ref(5)
const mode = ref<'mock'>('mock')
const loading = ref(false)
const errorMessage = ref('')
const response = ref<AskResponse | null>(null)

watch(
  () => props.paperId,
  () => {
    errorMessage.value = ''
    response.value = null
  },
)

async function ask() {
  if (!props.paperId || !question.value.trim()) return

  loading.value = true
  errorMessage.value = ''
  response.value = null
  try {
    response.value = await askPaper(props.paperId, {
      question: question.value.trim(),
      mode: mode.value,
      top_k: topK.value,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel-card">
    <h2 class="mb-3 text-sm font-semibold text-gray-950">Ask Paper</h2>

    <div v-if="!paperId" class="text-sm text-gray-500">Select a paper before asking.</div>

    <div v-else class="space-y-3">
      <textarea
        v-model="question"
        class="input min-h-24 resize-y"
        placeholder="Ask a question about this paper"
      />

      <div class="grid grid-cols-[1fr_1fr_auto] items-end gap-2">
        <label class="block">
          <span class="mb-1 block text-xs text-gray-500">top_k</span>
          <input v-model.number="topK" class="input" max="10" min="1" type="number" />
        </label>
        <label class="mode-control text-xs text-gray-500">
          <span>mode</span>
          <input v-model="mode" class="mode-select" disabled type="text" />
        </label>
        <button class="button-primary h-9 px-4" type="button" :disabled="loading || !question.trim()" @click="ask">
          {{ loading ? 'Asking...' : 'Ask' }}
        </button>
      </div>

      <p v-if="errorMessage" class="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
        {{ errorMessage }}
      </p>

      <div v-if="response" class="space-y-4">
        <div>
          <h3 class="mb-1 text-xs font-medium uppercase tracking-normal text-gray-500">Answer</h3>
          <p class="max-h-56 overflow-auto whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm leading-6 text-gray-800">
            {{ response.answer }}
          </p>
        </div>

        <div>
          <h3 class="mb-1 text-xs font-medium uppercase tracking-normal text-gray-500">Evidence Indices</h3>
          <p class="text-sm text-gray-700">{{ response.evidence_chunk_indices.join(', ') || '-' }}</p>
        </div>

        <div>
          <h3 class="mb-2 text-xs font-medium uppercase tracking-normal text-gray-500">Evidence Chunks</h3>
          <div class="space-y-2">
            <article
              v-for="chunk in response.evidence_chunks"
              :key="chunk.chunk_index"
              class="rounded-xl border border-gray-200 bg-white p-3 text-xs text-gray-700"
            >
              <div class="mb-2 flex flex-wrap gap-1.5">
                <span class="badge badge-muted">chunk {{ chunk.chunk_index }}</span>
                <span class="badge badge-score">score {{ chunk.score.toFixed(2) }}</span>
                <span class="badge badge-muted">pages {{ chunk.page_start ?? '-' }}-{{ chunk.page_end ?? '-' }}</span>
                <span class="badge badge-rank">{{ chunk.retrieval_method || '-' }}</span>
                <span class="badge badge-muted">
                  {{ chunk.matched_terms?.length ? chunk.matched_terms.join(', ') : '-' }}
                </span>
              </div>
              <p class="max-h-32 overflow-auto whitespace-pre-wrap leading-5">{{ chunk.text.slice(0, 700) }}</p>
            </article>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

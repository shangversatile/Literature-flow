<script setup lang="ts">
import { ref } from 'vue'
import { askLibrary } from '../api/libraryRag'
import type { LibraryAskResponse, ResearchTopic } from '../types'

defineProps<{
  topics: ResearchTopic[]
}>()

const question = ref('')
const mode = ref<'mock' | 'openai'>('openai')
const topK = ref(10)
const topic = ref('ALL')
const loading = ref(false)
const errorMessage = ref('')
const response = ref<LibraryAskResponse | null>(null)
const resultVisible = ref(false)

async function ask() {
  const cleanQuestion = question.value.trim()
  if (!cleanQuestion) return

  loading.value = true
  errorMessage.value = ''
  response.value = null
  resultVisible.value = false
  try {
    response.value = await askLibrary({
      question: cleanQuestion,
      mode: mode.value,
      top_k: topK.value,
      topic: topic.value === 'ALL' ? null : topic.value,
    })
    resultVisible.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loading.value = false
  }
}

function clearAnswer() {
  response.value = null
  errorMessage.value = ''
  resultVisible.value = false
}

function shortText(text: string) {
  return text.length > 600 ? `${text.slice(0, 600)}...` : text
}
</script>

<template>
  <section class="workspace-card px-4 py-3">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-gray-950">Ask Library</h2>
        <p class="text-xs text-gray-500">Cross-paper RAG over saved paper chunks.</p>
      </div>
      <button class="button-primary" type="button" :disabled="loading || !question.trim()" @click="ask">
        {{ loading ? 'Asking...' : 'Ask Library' }}
      </button>
    </div>

    <div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_160px_120px_220px]">
      <textarea
        v-model="question"
        class="input min-h-20 resize-y"
        placeholder="What are the main bottlenecks in LLM inference systems?"
      />
      <label class="block">
        <span class="mb-1 block text-xs text-gray-500">mode</span>
        <select v-model="mode" class="input">
          <option value="openai">openai</option>
          <option value="mock">mock</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-gray-500">top_k</span>
        <input v-model.number="topK" class="input" max="30" min="1" type="number" />
      </label>
      <label class="block">
        <span class="mb-1 block text-xs text-gray-500">topic</span>
        <select v-model="topic" class="input">
          <option value="ALL">All</option>
          <option v-for="item in topics" :key="item.id" :value="item.name">{{ item.name }}</option>
        </select>
      </label>
    </div>

    <p v-if="errorMessage" class="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ errorMessage }}
    </p>

    <div v-if="response" class="mt-4">
      <div class="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div class="flex flex-wrap gap-2">
          <button class="button-ghost" type="button" @click="clearAnswer">Clear Answer</button>
          <button class="button-ghost" type="button" @click="resultVisible = !resultVisible">
            {{ resultVisible ? 'Hide Results' : 'Show Results' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="response && resultVisible" class="mt-2 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <div>
        <h3 class="mb-1 text-xs font-medium uppercase tracking-normal text-gray-500">Answer</h3>
        <p class="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm leading-6 text-gray-800">
          {{ response.answer }}
        </p>
        <div class="mt-2 flex flex-wrap gap-1.5 text-xs text-gray-600">
          <span class="badge badge-muted">mode {{ response.mode }}</span>
          <span class="badge badge-muted">topic {{ response.topic || 'All' }}</span>
          <span class="badge badge-score">{{ response.evidence_count }} evidence</span>
        </div>
      </div>

      <div>
        <h3 class="mb-2 text-xs font-medium uppercase tracking-normal text-gray-500">Evidence Chunks</h3>
        <div class="max-h-80 space-y-2 overflow-auto pr-1">
          <article
            v-for="chunk in response.evidence_chunks"
            :key="`${chunk.paper_id}-${chunk.chunk_index}`"
            class="rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700"
          >
            <h4 class="mb-1 line-clamp-2 font-semibold leading-5 text-gray-950">{{ chunk.paper_title }}</h4>
            <div class="mb-2 flex flex-wrap gap-1.5">
              <span class="badge badge-muted">{{ chunk.paper_year || '-' }} / {{ chunk.paper_venue || '-' }}</span>
              <span class="badge badge-muted">paper {{ chunk.paper_id }}</span>
              <span class="badge badge-muted">chunk {{ chunk.chunk_index }}</span>
              <span class="badge badge-score">score {{ chunk.score.toFixed(2) }}</span>
              <span class="badge badge-rank">{{ chunk.retrieval_method }}</span>
            </div>
            <div class="mb-2 text-gray-500">
              matched_terms: {{ chunk.matched_terms.length ? chunk.matched_terms.join(', ') : '-' }}
            </div>
            <p class="max-h-36 overflow-auto whitespace-pre-wrap leading-5">{{ shortText(chunk.text) }}</p>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>
